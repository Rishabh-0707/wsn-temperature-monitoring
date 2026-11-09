#!/usr/bin/env python3
"""Fail unless a completed Cooja experiment has evidence of delivery and multi-hop."""
import argparse
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis.performance_analysis import load_experiment

def validate(config, result_dir=None):
    tree = ET.parse(config)
    metadata = json.loads(config.with_suffix('.json').read_text())
    motes = tree.findall('./simulation/mote')
    assert len(motes) == metadata['nodes'] + 1, 'Wrong mote count'
    assert len(tree.findall('./simulation/motetype')) == 2, 'Require sink and sensor types'
    ids = [int(m.find("./interface_config[id]/id").text) for m in motes]
    assert sorted(ids) == list(range(1, metadata['nodes'] + 2))
    assert tree.find('./plugin/plugin_config/active').text == 'true'
    if result_dir:
        run, events, readings = load_experiment(result_dir)
        assert run['validation'] and run['validation']['multihop'], 'No completed multi-hop evidence'
        assert 'TEST OK' in (result_dir / 'COOJA.testlog').read_text(), 'Cooja did not pass'
        assert {r['node_id'] for r in readings} == set(range(1, run['nodes'] + 1)), 'Missing sensor receptions'
        outer = {p['node_id'] for p in run['topology'] if (p['x']**2+p['y']**2)**.5 > run['radio_range_m']}
        assert outer & {r['node_id'] for r in readings}, 'No reception outside direct range'
        assert any(e['type']=='status' and e['node_id'] in outer and e['parent_mote_id']>1 for e in events)
        assert any(e['type']=='tx' for e in events) and any(e['type']=='energy' for e in events)
        print(f"PASS: {run['nodes']} sensors, {len(readings)} unique receptions, outer nodes {sorted(outer)}")
    else: print(f"PASS: configuration contains one sink and {metadata['nodes']} sensors")

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('config',type=Path);p.add_argument('--results',type=Path)
    a=p.parse_args();validate(a.config,a.results)
