from datetime import datetime, timezone
import sqlite3
import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.services import summarize
from scripts.bridge import parse_line

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "test.sqlite3")) as c:
        response = c.post("/api/runs", json={"run_id": "test", "name": "Test experiment", "nodes": 2,
            "started_at": "2026-11-09T00:00:00Z", "duration_s": 10, "telemetry_complete": True})
        assert response.status_code == 201
        yield c

def event(kind, sequence, time, identity, **kwargs):
    return dict(event_id=identity, type=kind, node_id=1, boot_id=9, sequence_number=sequence,
                sim_time_us=time, temperature_centi=2500, attempt=1, **kwargs)

def test_metrics_retry_duplicate_loss_delay_and_persistence(client):
    items = [event("tx", 1, 1000000, "a"), event("tx", 1, 2000000, "b"),
             event("rx", 1, 2100000, "c"), event("rx", 1, 2200000, "d"),
             event("tx", 2, 3000000, "e"), event("tx", 3, 4000000, "f"), event("rx", 3, 4020000, "g")]
    assert client.post("/api/runs/test/events", json=items).json()["inserted"] == 7
    assert client.post("/api/runs/test/events", json=items).json()["inserted"] == 0
    client.post("/api/runs/test/complete")
    s = client.get("/api/network/statistics").json()
    assert s["packets_sent"] == 3 and s["packets_received"] == 2 and s["packets_lost"] == 1
    assert s["pdr"] == pytest.approx(200 / 3)
    assert s["average_delay_ms"] == 560
    assert s["throughput_bps"] == 28.8
    assert s["duplicate_receptions"] == 1 and s["retry_attempts"] == 1
    assert s["sequence_gaps"] == 1
    for path in ["/api/readings/latest", "/api/nodes", "/api/network/health", "/api/dashboard", "/api/export/readings.csv"]:
        assert client.get(path).status_code == 200
    assert client.get("/api/readings?node_id=1&limit=1").json()["total"] == 2
    assert client.get("/api/readings?node_id=2").json()["total"] == 0
    with sqlite3.connect(client.app.state.db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM readings").fetchone()[0] == 2
    with TestClient(create_app(client.app.state.db_path)) as reopened:
        assert reopened.get("/api/readings").json()["total"] == 2

def test_out_of_order_and_boot_reset(client):
    items = [event("tx", 3, 1000000, "a"), event("rx", 3, 1100000, "b")]
    client.post("/api/runs/test/events", json=items)
    assert client.get("/api/nodes").json()[0]["sequence_gaps"] == 2
    client.post("/api/runs/test/events", json=[event("rx", 1, 500000, "c"), event("rx", 2, 900000, "d")])
    e = event("rx", 1, 3000000, "e"); e["boot_id"] = 10
    client.post("/api/runs/test/events", json=[e])
    assert client.get("/api/nodes").json()[0]["sequence_gaps"] == 0
    assert client.get("/api/readings/latest").json()[0]["boot_id"] == 10
    assert client.get("/api/readings").json()["total"] == 4

def test_validation_and_transaction_rollback(client):
    malformed = event("tx", 1, 1, "a"); del malformed["attempt"]
    assert client.post("/api/runs/test/events", json=[malformed]).status_code == 422
    bad = event("tx", 2, 20000000, "b")
    assert client.post("/api/runs/test/events", json=[event("tx", 1, 1, "a"), bad]).status_code == 422
    assert client.get("/api/network/statistics").json()["packets_sent"] == 0
    client.post("/api/runs/test/events", json=[event("tx", 1, 1, "a")])
    assert client.post("/api/runs/test/events", json=[event("tx", 2, 1, "a")]).status_code == 409
    assert client.get("/api/readings?limit=10001").status_code == 422
    assert client.get("/api/readings?since=2026-01-01T00:00:00").status_code == 422

def test_receive_only_no_fabricated_pdr(client):
    body = {"node_id": 1, "temperature": 22.5, "sequence_number": 1, "timestamp": "2026-11-09T00:00:00Z"}
    assert client.post("/api/readings", json=body).status_code == 201
    assert client.post("/api/readings", json=body).json()["status"] == "duplicate"
    stats = client.get("/api/network/statistics?run_id=manual").json()
    assert stats["pdr"] is None and stats["packets_sent"] is None
    assert client.post("/api/readings", json={**body, "temperature": 200}).status_code == 422
    assert client.post("/api/readings", json={**body, "timestamp": "2026-11-09T00:00:00"}).status_code == 422
    assert client.post("/api/readings", json={**body, "run_id": "test"}).status_code == 409

def test_energy_and_offline_node(client):
    e = {"type": "energy", "event_id": "energy", "node_id": 1, "sim_time_us": 10000000,
         "cpu": 1000, "lpm": 9000, "deep_lpm": 0, "transmit": 100, "listen": 9900, "ticks_per_second": 1000}
    assert client.post("/api/runs/test/events", json=[e]).status_code == 200
    stats = client.get("/api/network/statistics").json()
    expected = 3 * (1 * .0018 + 9 * .000005 + .1 * .0174 + 9.9 * .0188)
    assert stats["estimated_energy_j"] == pytest.approx(expected)
    assert stats["active_nodes"] == 0
    assert stats["pdr"] is None

def test_bridge_control_parser():
    import json
    line = 'WSN_EVENT ' + json.dumps({"sim_time_us": 123, "mote_id": 2, "message": "[INFO: RPL] sending a multicast-DIO with rank 128"})
    e = parse_line(line, 1)
    assert e["type"] == "control" and e["control_kind"] == "DIO" and e["node_id"] == 1
    assert parse_line(line, 1)["event_id"] == e["event_id"]
    assert parse_line("Random seed: 1", 1) is None
