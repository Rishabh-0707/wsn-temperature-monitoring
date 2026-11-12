#!/usr/bin/env python3
"""Run isolated real simulator variants and export their observed results."""
import argparse,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from analysis.ns3_analysis import export
from backend.app.ns3_config import Ns3Config

def matrix(url):
    variants=[('star_5',dict(nodes=5,topology='star')),('ladder_10',dict(nodes=10,topology='ladder')),('ladder_20',dict(nodes=20,topology='ladder')),('interval_2',dict(nodes=10,topology='ladder',interval_s=2)),('interval_10',dict(nodes=10,topology='ladder',interval_s=10)),('loss_03',dict(nodes=10,topology='ladder',loss_probability=.3)),('range_35',dict(nodes=10,topology='ladder',radio_range_m=35)),('seed_42',dict(nodes=10,topology='ladder',seed=42))]
    results=[];out=Path(__file__).resolve().parents[1]/'ns3/results/matrix.json'
    with httpx.Client(base_url=url,timeout=60) as client:
        for label,values in variants:
            config=Ns3Config(duration_s=300,realtime=False,**values)
            r=client.post('/api/simulations/ns3/run',json=config.model_dump());r.raise_for_status();run_id=r.json()['run_id'];deadline=time.monotonic()+660
            while True:
                r=client.get(f'/api/simulations/ns3/{run_id}/execution');r.raise_for_status();status=r.json()['run']['status']
                if status not in ('running','ingesting'):break
                if time.monotonic()>deadline:raise TimeoutError(run_id)
                time.sleep(.5)
            metrics=export(run_id,url);results.append(dict(label=label,run_id=run_id,status=status,statistics=metrics));out.write_text(json.dumps(results,indent=2)+'\n');print(label,status,metrics['packets_received'],flush=True)
            if status!='completed':raise RuntimeError(f'Experiment process failed: {run_id}')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--url',default='http://127.0.0.1:8001');matrix(p.parse_args().url)
