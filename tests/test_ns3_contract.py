from fastapi.testclient import TestClient
from backend.app.main import create_app

def test_ns3_isolation_replay_and_historical_clock(tmp_path):
    database=tmp_path/'test.sqlite3'
    with TestClient(create_app(database)) as client:
        common=dict(name='contract',started_at='2026-01-01T00:00:00Z',duration_s=30,nodes=1,telemetry_complete=True)
        old=dict(common,run_id='old',source='cooja')
        new=dict(common,run_id='new',source='ns3',simulator='ns3',nodes=2)
        assert client.post('/api/runs',json=old).status_code==201
        assert client.post('/api/runs',json=old).status_code==201
        assert client.post('/api/runs',json=new).status_code==201
        assert client.post('/api/runs',json=dict(new,run_id='bad',simulator='cooja')).status_code==422
        events=[dict(event_id='tx',type='tx',node_id=1,boot_id=1,sequence_number=1,temperature_centi=2850,attempt=1,sim_time_us=20000000),dict(event_id='rx',type='rx',node_id=1,boot_id=1,sequence_number=1,temperature_centi=2850,attempt=1,sim_time_us=20100000,hop_count=2,path=[1,2,0])]
        assert client.post('/api/runs/new/events',json=events).json()['inserted']==2
        assert client.post('/api/runs/new/events',json=events).json()['inserted']==0
        client.post('/api/runs/new/complete')
        s=client.get('/api/dashboard?run_id=new').json()
        assert s['run']['simulator']=='ns3'
        assert s['statistics']['active_nodes']==1
        assert s['statistics']['average_hop_count']==2
        assert s['statistics']['average_delay_ms']==100
        assert client.get('/api/readings?run_id=old').json()['total']==0
        assert client.get('/api/runs/new/events').json()['total']==2
        assert client.get('/api/comparison?cooja=old&ns3=new').status_code==200
        assert client.get('/api/comparison?cooja=new&ns3=old').status_code==422
    with TestClient(create_app(database)) as reopened:
        assert reopened.get('/api/readings?run_id=new').json()['total']==1

def test_ns3_config_rejects_unbounded_and_shell_inputs():
    import pytest
    from pydantic import ValidationError
    from backend.app.ns3_config import Ns3Config
    for body in [{'nodes':33},{'duration_s':99999},{'topology':'star;touch /tmp/bad'},{'command':'anything'},{'payload_bytes':20},{'loss_probability':float('nan')},{'temperature_min_c':40,'temperature_max_c':30}]:
        with pytest.raises(ValidationError):Ns3Config.model_validate(body)


def test_ns3_path_validation_is_transactional(tmp_path):
    with TestClient(create_app(tmp_path/'bounds.sqlite3')) as client:
        client.post('/api/runs',json=dict(run_id='bounds',source='ns3',simulator='ns3',name='bounds',nodes=1,duration_s=30,started_at='2026-01-01T00:00:00Z',telemetry_complete=True))
        good=dict(event_id='start',type='started',node_id=0,sim_time_us=0)
        bad=dict(event_id='bad',type='forward',node_id=1,sim_time_us=1,path=[1,2,0])
        assert client.post('/api/runs/bounds/events',json=[good,bad]).status_code==422
        assert client.get('/api/runs/bounds/events').json()['total']==0
        bad['path']=[-1,0]
        assert client.post('/api/runs/bounds/events',json=[bad]).status_code==422


def test_managed_restart_preserves_history_and_marks_interrupted(tmp_path):
    db=tmp_path/'restart.sqlite3'
    with TestClient(create_app(db)) as client:
        for rid,source,managed in [('old','cooja',False),('unfinished','ns3',True)]:
            client.post('/api/runs',json=dict(run_id=rid,source=source,name=rid,nodes=1,duration_s=30,started_at='2026-01-01T00:00:00Z',managed_ns3=managed))
    with TestClient(create_app(db)) as client:
        runs={r['run_id']:r for r in client.get('/api/runs').json()}
        assert runs['old']['status']=='running'
        assert runs['unfinished']['status']=='interrupted'


def test_ns3_bridge_rejects_incomplete_recording_before_api_call(tmp_path):
    import json,pytest
    from scripts.ns3_bridge import ingest
    (tmp_path/'manifest.json').write_text(json.dumps(dict(source='ns3',simulator='ns3',run_id='partial')))
    (tmp_path/'events.jsonl').write_text(json.dumps(dict(run_id='partial',simulator='ns3',event_id='e1',type='started',node_id=0,sim_time_us=0))+'\n')
    with pytest.raises(ValueError,match='incomplete'):ingest(tmp_path,'http://127.0.0.1:1')


def test_execution_status_survives_incomplete_artifact(tmp_path, monkeypatch):
    from backend.app import ns3_jobs
    monkeypatch.setattr(ns3_jobs, 'ROOT', tmp_path)
    with TestClient(create_app(tmp_path/'status.sqlite3')) as client:
        client.post('/api/runs',json=dict(run_id='recorded',source='ns3',name='recorded',nodes=1,duration_s=30,started_at='2026-01-01T00:00:00Z'))
        client.post('/api/runs/recorded/complete')
        directory=tmp_path/'ns3/results/recorded';directory.mkdir(parents=True)
        (directory/'execution.json').write_text('{')
        (directory/'console.log').write_text('')
        response=client.get('/api/simulations/ns3/recorded/execution')
        assert response.status_code==200
        assert response.json()['run']['status']=='completed'
        assert response.json()['artifact_error']
        assert not response.json()['can_stop']


def test_exited_process_is_ingesting_not_running(tmp_path):
    from types import SimpleNamespace
    app=create_app(tmp_path/'ingesting.sqlite3')
    with TestClient(app) as client:
        client.post('/api/runs',json=dict(run_id='finishing',source='ns3',name='finishing',nodes=1,duration_s=30,started_at='2026-01-01T00:00:00Z'))
        app.state.ns3_jobs.jobs['finishing']={'process':SimpleNamespace(poll=lambda:0)}
        assert client.get('/api/runs').json()[0]['status']=='ingesting'
        assert client.get('/api/dashboard?run_id=finishing').json()['run']['status']=='ingesting'
        app.state.ns3_jobs.jobs.clear()
