#!/usr/bin/env python3
"""Independently verify real NS-3 recordings, API metrics and NetAnim output."""
import argparse
from collections import Counter
import csv
import io
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import httpx
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.ns3_bridge import parse_event


def validate(directory, client):
    manifest = json.loads((directory / 'manifest.json').read_text())
    run_id = manifest['run_id']
    events = [parse_event(line, run_id) for line in (directory / 'events.jsonl').read_text().splitlines()]
    assert events[0]['type'] == 'started' and events[-1]['type'] == 'completed'
    assert len({e['event_id'] for e in events}) == len(events)
    assert all(a['sim_time_us'] <= b['sim_time_us'] for a, b in zip(events, events[1:]))
    key = lambda e: (e['node_id'], e['boot_id'], e['sequence_number'])
    tx, rx = {}, {}
    counts = Counter(e['type'] for e in events)
    for e in events:
        if e['type'] == 'tx': tx.setdefault(key(e), e)
        if e['type'] == 'rx':
            rx.setdefault(key(e), e)
            assert e['path'][0] == e['node_id'] and e['path'][-1] == 0
            assert e['hop_count'] >= 1
            assert 1 <= e['attempt'] <= manifest['configuration']['max_attempts']
        if e['type'] == 'energy':
            assert e['transmit'] + e['listen'] <= e['sim_time_us']
    response = client.get('/api/dashboard', params={'run_id': run_id}); response.raise_for_status()
    snapshot = response.json(); s = snapshot['statistics']
    assert snapshot['run']['status'] == 'completed'
    assert s['packets_sent'] == len(tx) and s['packets_received'] == len(rx)
    assert s['packets_lost'] == len(tx.keys() - rx.keys())
    assert s['transmission_attempts'] == counts['tx']
    assert s['retry_attempts'] == counts['tx'] - len(tx)
    assert s['duplicate_receptions'] == counts['rx'] - len(rx)
    assert s['failed_ack_samples'] == counts['failed']
    assert s['no_route_samples'] == counts['no_route']
    assert s['generated_samples'] == len(tx) + counts['no_route']
    assert math.isclose(s['throughput_bps'], len(rx)*18*8/manifest['duration_s'])
    if tx: assert math.isclose(s['pdr'], len(rx.keys() & tx.keys())/len(tx)*100)
    else: assert s['pdr'] is None and s['packet_loss_ratio'] is None
    if rx:
        delays = [(v['sim_time_us'] - tx[k]['sim_time_us']) / 1000 for k, v in rx.items()]
        assert math.isclose(s['average_delay_ms'], sum(delays)/len(delays))
        assert math.isclose(s['average_hop_count'], sum(v['hop_count'] for v in rx.values())/len(rx))
    csv_response = client.get('/api/export/readings.csv', params={'run_id': run_id});csv_response.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(csv_response.text)))
    assert len(rows) == len(rx) and all(r['run_id'] == run_id for r in rows)
    tree = ET.parse(directory/'animation.xml')
    assert tree.getroot().tag == 'anim'
    assert len(tree.findall('.//node')) == manifest['nodes'] + 1
    assert tree.findall('.//pr') or tree.findall('.//p')
    return dict(run_id=run_id, events=len(events), unique_tx=len(tx), unique_rx=len(rx),
                forwarding_events=counts['forward'], max_hops=max((e['hop_count'] for e in rx.values()), default=0),
                netanim_xml='parsed; node and wireless packet records present', csv_rows=len(rows))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url', default='http://127.0.0.1:8001')
    p.add_argument('--matrix', type=Path, default=ROOT/'ns3/results/matrix.json')
    args=p.parse_args()
    with httpx.Client(base_url=args.url, timeout=60) as client:
        checks=[validate(ROOT/'ns3/results'/r['run_id'], client) for r in json.loads(args.matrix.read_text())]
    print(json.dumps(checks, indent=2))
