import json
import time
import pytest
from scripts import bridge

class FakeClient:
    def __init__(self, *args, **kwargs): pass
    def __enter__(self): return self
    def __exit__(self, *args): pass

def test_live_tail_buffers_partial_lines_and_terminates(tmp_path, monkeypatch):
    manifest = tmp_path / 'manifest.json'
    manifest.write_text(json.dumps({'run_id': 'live'}))
    logfile = tmp_path / 'COOJA.testlog'
    line = 'WSN_EVENT ' + json.dumps({'sim_time_us': 1, 'mote_id': 2,
        'message': json.dumps({'type':'sample','node_id':1,'boot_id':1,'sequence_number':1})})
    logfile.write_text(line[:30])
    posts = []
    monkeypatch.setattr(bridge.httpx, 'Client', FakeClient)
    def post(client, path, body=None):
        posts.append((path, body))
        return {'inserted': len(body)} if path.endswith('/events') else {}
    monkeypatch.setattr(bridge, 'post', post)
    def finish_write(seconds):
        with logfile.open('a') as f:
            f.write(line[30:] + '\nWSN_META {"type":"end"}\n')
    monkeypatch.setattr(bridge.time, 'sleep', finish_write)
    result = bridge.import_log(logfile, manifest, 'unused', follow=True)
    assert result['inserted'] == 1 and result['completed']
    event_batch = next(body for path, body in posts if path.endswith('/events'))
    assert event_batch[0] == bridge.parse_line(line + '\n', 1)
    assert posts[-1][0].endswith('/complete')

def test_live_tail_reports_stopped_producer(tmp_path, monkeypatch):
    manifest = tmp_path / 'manifest.json'; manifest.write_text('{"run_id":"stopped"}')
    logfile = tmp_path / 'COOJA.testlog'; logfile.write_text('')
    monkeypatch.setattr(bridge.httpx, 'Client', FakeClient)
    monkeypatch.setattr(bridge, 'post', lambda *args, **kwargs: {})
    clock = iter([0.0, 31.0])
    monkeypatch.setattr(bridge.time, 'monotonic', lambda: next(clock))
    with pytest.raises(TimeoutError, match='No simulator output'):
        bridge.import_log(logfile, manifest, 'unused', follow=True, idle_timeout=30)
