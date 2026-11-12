#!/usr/bin/env python3
"""Launch and follow a validated experiment on the unified local backend."""
import argparse,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from backend.app.ns3_config import Ns3Config

def run(config,url):
    with httpx.Client(base_url=url,timeout=30) as client:
        response=client.post('/api/simulations/ns3/run',json=config.model_dump());response.raise_for_status();meta=response.json();run_id=meta['run_id'];print(run_id,flush=True)
        deadline=time.monotonic()+config.duration_s*2+120
        while time.monotonic()<deadline:
            response=client.get(f'/api/simulations/ns3/{run_id}/execution');response.raise_for_status();state=response.json()
            if state['run']['status'] not in ('running','ingesting'):
                print(json.dumps(state,indent=2));return 0 if state['run']['status']=='completed' else 1
            time.sleep(1)
        raise TimeoutError('Backend did not report a terminal state')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('nodes',type=int,nargs='?',default=5);p.add_argument('--topology',choices=['star','ladder']);p.add_argument('--duration',type=int,default=60);p.add_argument('--interval',type=float,default=5);p.add_argument('--range',type=float,default=50);p.add_argument('--seed',type=int,default=123456);p.add_argument('--loss',type=float,default=0);p.add_argument('--fast',action='store_true');p.add_argument('--url',default='http://127.0.0.1:8001')
    a=p.parse_args();sys.exit(run(Ns3Config(nodes=a.nodes,topology=a.topology or ('star' if a.nodes==5 else 'ladder'),duration_s=a.duration,interval_s=a.interval,radio_range_m=a.range,seed=a.seed,loss_probability=a.loss,realtime=not a.fast),a.url))
