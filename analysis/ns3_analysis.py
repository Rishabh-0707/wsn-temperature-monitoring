#!/usr/bin/env python3
"""Export recorded NS-3 evidence and render per-run graphs from the shared API."""
import argparse,csv,json,os
from pathlib import Path
import httpx
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/wsn-ns3-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def export(run_id,url):
    with httpx.Client(base_url=url,timeout=60) as c:
        response=c.get('/api/dashboard',params={'run_id':run_id});response.raise_for_status();snapshot=response.json()
        if snapshot['run']['source']!='ns3':raise ValueError('This exporter writes NS-3 results only')
        directory=ROOT/'ns3/results'/run_id;directory.mkdir(parents=True,exist_ok=True)
        (directory/'summary.json').write_text(json.dumps(snapshot,indent=2)+'\n')
        response=c.get('/api/export/readings.csv',params={'run_id':run_id});response.raise_for_status();(directory/'readings.csv').write_bytes(response.content)
    stats=snapshot['statistics'];nodes=snapshot['nodes']
    with (directory/'metrics.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['metric','value']);w.writerows((k,v) for k,v in stats.items() if not isinstance(v,(dict,list)))
    with (directory/'nodes.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(nodes[0]) if nodes else ['node_id']);w.writeheader();w.writerows(nodes)
    fig,axes=plt.subplots(1,3,figsize=(13,4));ids=[n['node_id'] for n in nodes]
    axes[0].bar(ids,[n['packets_received'] for n in nodes]);axes[0].set(title='Unique sink receptions',xlabel='Sensor',ylabel='Packets')
    axes[1].bar(ids,[n['pdr'] or 0 for n in nodes]);axes[1].set(title='Delivery ratio (no TX shown as 0)',xlabel='Sensor',ylabel='Percent',ylim=(0,105))
    axes[2].bar(ids,[n['energy_j'] or 0 for n in nodes]);axes[2].set(title='Estimated energy',xlabel='Sensor',ylabel='Joules')
    fig.suptitle(snapshot['run']['name']);fig.tight_layout();fig.savefig(directory/'performance.png',dpi=150);fig.savefig(directory/'performance.svg');plt.close(fig)
    return stats
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run_id');p.add_argument('--url',default='http://127.0.0.1:8001');a=p.parse_args();print(json.dumps(export(a.run_id,a.url),indent=2))
