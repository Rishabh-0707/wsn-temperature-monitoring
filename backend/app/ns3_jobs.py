"""Single-process, bounded local NS-3 job execution. Never invokes a shell."""
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import threading
import time
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Request
from .database import connect
from .models import Run, Event
from .ns3_config import Ns3Config
from .routes import create_run, ingest_events, resolve_run, run_state

ROOT=Path(__file__).resolve().parents[2]
router=APIRouter(prefix='/api/simulations/ns3')

class Jobs:
    def __init__(self,app):
        self.app=app;self.lock=threading.Lock();self.jobs={};self.closing=False
        with connect(app.state.db_path) as db:
            for row in db.execute("SELECT run_id,metadata FROM runs WHERE source='ns3' AND status='running'"):
                if json.loads(row['metadata']).get('managed_ns3'):
                    db.execute("UPDATE runs SET status='interrupted' WHERE run_id=?",(row['run_id'],))
    def start(self,config):
        runtime=Path(os.environ.get('NS3_RUNTIME',(ROOT/'.runtime/ns3-runtime-path').read_text().strip() if (ROOT/'.runtime/ns3-runtime-path').exists() else ROOT/'.runtime/ns3-runtime'))
        executable=runtime/'scratch/wsn-platform/ns3.46-wsn-temperature-default'
        if not executable.is_file():raise HTTPException(503,'Build NS-3 with bash scripts/build_ns3.sh first')
        with self.lock:
            if self.closing or any(j['thread'].is_alive() for j in self.jobs.values()):raise HTTPException(409,'An NS-3 experiment is already running')
            run_id=str(uuid4());directory=ROOT/'ns3/results'/run_id;directory.mkdir(parents=True,exist_ok=False)
            positions=[dict(node_id=0,mote_id=1,x=0,y=0)]
            for i in range(1,config.nodes+1):
                x,y=(30*math.cos(i*2*math.pi/config.nodes),30*math.sin(i*2*math.pi/config.nodes)) if config.topology=='star' else (35*((i+1)//2),0 if i%2 else 25)
                positions.append(dict(node_id=i,mote_id=i+1,x=x,y=y))
            metadata=dict(run_id=run_id,name=f'NS-3 · {config.nodes} sensors · {config.topology}',source='ns3',simulator='ns3',started_at=datetime.now(timezone.utc).isoformat(),duration_s=config.duration_s,nodes=config.nodes,telemetry_complete=True,configuration=config.model_dump(),topology=positions,radio_range_m=config.radio_range_m,simulator_version='3.46',routing_protocol='IPv6 static BFS routes (not RPL)',wireless_model='LR-WPAN / SixLoWPAN / IPv6 / UDP; range propagation',managed_ns3=True)
            provenance=runtime/'wsn-build.json'
            if not provenance.is_file():raise HTTPException(503,'Rebuild NS-3 to generate build provenance')
            build=json.loads(provenance.read_text())
            if hashlib.sha256(executable.read_bytes()).hexdigest()!=build['binary_sha256']:
                raise HTTPException(503,'NS-3 executable changed; rebuild before running')
            metadata.update(build)
            request=SimpleNamespace(app=self.app)
            result=create_run(Run.model_validate(metadata),request)
            (directory/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
            job={'process':None,'cancel':threading.Event(),'directory':directory,'error':None}
            thread=threading.Thread(target=self.execute,args=(run_id,config,executable,job),daemon=True);job['thread']=thread;self.jobs[run_id]=job;thread.start()
            return result
    def execute(self,run_id,config,executable,job):
        request=SimpleNamespace(app=self.app);directory=job['directory'];status='failed';completed=False;process=None
        args=[str(executable),f'--nodes={config.nodes}',f'--duration={config.duration_s}',f'--interval={config.interval_s}',f'--range={config.radio_range_m}',f'--seed={config.seed}',f'--topology={config.topology}',f'--loss={config.loss_probability}',f'--minTemp={config.temperature_min_c}',f'--maxTemp={config.temperature_max_c}',f'--timeout={config.ack_timeout_s}',f'--attempts={config.max_attempts}',f'--realtime={int(config.realtime)}',f'--runId={run_id}',f'--output={directory / "events.jsonl"}',f'--animation={directory / "animation.xml"}']
        try:
            start=time.monotonic();buffer=''
            with (directory/'console.log').open('w') as console:
                process=subprocess.Popen(args,cwd=directory,stdout=console,stderr=subprocess.STDOUT,start_new_session=True)
                job['process']=process
                logfile=directory/'events.jsonl'
                while not logfile.exists() and process.poll() is None:
                    if job['cancel'].wait(.1) or time.monotonic()-start>30:break
                if not logfile.exists():raise RuntimeError('Simulator did not create its event log')
                with logfile.open() as stream:
                    while True:
                        if job['cancel'].is_set():
                            status='cancelled';break
                        if time.monotonic()-start>config.duration_s*2+60:raise TimeoutError('Simulation wall-time limit exceeded')
                        chunk=stream.read(65536);buffer+=chunk;lines=buffer.split('\n');buffer=lines.pop();batch=[]
                        for line in lines:
                            value=json.loads(line)
                            if value.pop('run_id',None)!=run_id or value.pop('simulator',None)!='ns3':raise ValueError('Event provenance mismatch')
                            event=Event.model_validate(value);batch.append(event)
                            if event.type=='completed':completed=True
                            if len(batch)==200:ingest_events(run_id,batch,request);batch=[]
                        if batch:ingest_events(run_id,batch,request)
                        if not chunk and process.poll() is not None:
                            if process.returncode!=0 or not completed or buffer:raise RuntimeError('Simulator ended without a valid completion event')
                            status='completed';break
                        if not chunk:job['cancel'].wait(.1)
        except Exception as error:
            status='cancelled' if job['cancel'].is_set() else 'failed'
            job['error']=None if status=='cancelled' else str(error)
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try:process.wait(timeout=3)
                except subprocess.TimeoutExpired:process.kill();process.wait(timeout=3)
            with connect(self.app.state.db_path) as db:db.execute('UPDATE runs SET status=? WHERE run_id=?',(status,run_id))
            terminal=directory/'execution.json.tmp'
            terminal.write_text(json.dumps({'status':status,'error':job['error'],'returncode':process.returncode if process else None},indent=2)+'\n')
            terminal.replace(directory/'execution.json')
    def close(self):
        self.closing=True
        for j in self.jobs.values():j['cancel'].set()
        for j in self.jobs.values():j['thread'].join(timeout=5)

@router.post('/run',status_code=202)
def launch(config:Ns3Config,request:Request):return request.app.state.ns3_jobs.start(config)

@router.post('/{run_id}/stop')
def stop(run_id:str,request:Request):
    job=request.app.state.ns3_jobs.jobs.get(run_id)
    if not job or not job['thread'].is_alive():raise HTTPException(409,'No active local NS-3 process for this run')
    job['cancel'].set();return {'run_id':run_id,'status':'cancelling'}

@router.get('/{run_id}/execution')
def execution(run_id:str,request:Request):
    with connect(request.app.state.db_path) as db:
        run=resolve_run(db,run_id)
        if run['source']!='ns3':raise HTTPException(404,'Not an NS-3 experiment')
    job=request.app.state.ns3_jobs.jobs.get(run_id)
    directory=ROOT/'ns3/results'/run_id
    details={}
    artifact_error=None
    try:
        if (directory/'execution.json').exists():
            details=json.loads((directory/'execution.json').read_text())
    except (OSError,ValueError) as error:
        artifact_error=f'Execution artifact unavailable: {error}'
    path=directory/'console.log'
    output=''
    try:
        if path.exists() and path.stat().st_size:
            with path.open('rb') as f:f.seek(max(0,path.stat().st_size-12000));output=f.read().decode(errors='replace')
    except OSError as error:
        artifact_error=f'Console artifact unavailable: {error}'
    process=job.get('process') if job else None
    return {'run':run_state(run,request),'error':job['error'] if job else details.get('error'),'artifact_error':artifact_error,'output':output,'can_stop':bool(job and job['thread'].is_alive() and (process is None or process.poll() is None))}
