#!/usr/bin/env python3
"""Import actual NS-3 JSON Lines through the existing run/event REST contract."""
import argparse
import json
from pathlib import Path
import sys
import httpx
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.models import Event
from scripts.bridge import post

def parse_event(line, run_id):
    value=json.loads(line)
    if value.pop('run_id',None)!=run_id or value.pop('simulator',None)!='ns3':
        raise ValueError('NS-3 event provenance does not match experiment')
    return Event.model_validate(value).model_dump(exclude_none=True)

def ingest(directory,url):
    directory=Path(directory);manifest=json.loads((directory/'manifest.json').read_text())
    if manifest.get('source')!='ns3' or manifest.get('simulator')!='ns3':raise ValueError('Not an NS-3 manifest')
    # Validate the entire completed recording before creating any database rows.
    with (directory/'events.jsonl').open() as stream:
        final=None
        for line in stream:
            final=parse_event(line,manifest['run_id'])
    if final is None or final['type']!='completed':
        raise ValueError('Recording is incomplete; use managed execution for live ingestion')
    completed=False;inserted=0;batch=[]
    with httpx.Client(base_url=url,timeout=30) as client:
        post(client,'/api/runs',manifest)
        with (directory/'events.jsonl').open() as stream:
            for line in stream:
                event=parse_event(line,manifest['run_id']);batch.append(event)
                completed=event['type']=='completed'
                if len(batch)==200:
                    inserted+=post(client,f"/api/runs/{manifest['run_id']}/events",batch)['inserted'];batch=[]
        if batch:inserted+=post(client,f"/api/runs/{manifest['run_id']}/events",batch)['inserted']
        if completed:post(client,f"/api/runs/{manifest['run_id']}/complete")
    return {'inserted':inserted,'completed':completed}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path);parser.add_argument('--url',default='http://127.0.0.1:8001')
    args=parser.parse_args();print(json.dumps(ingest(args.directory,args.url)))
