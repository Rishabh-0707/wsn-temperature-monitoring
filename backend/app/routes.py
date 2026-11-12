import csv
import io
import json
from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import Response
from .database import connect
from .models import Event, Reading, Run
from .services import summarize

router = APIRouter(prefix="/api")

def db_for(request):
    return connect(request.app.state.db_path)

def resolve_run(db, run_id=None):
    row = db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone() if run_id else db.execute(
        "SELECT * FROM runs ORDER BY started_at DESC LIMIT 1").fetchone()
    if row is None:
        raise HTTPException(404, "No experiment found. Run Cooja and import its log first.")
    return dict(row)

def run_public(row):
    result = dict(row)
    result["metadata"] = json.loads(result["metadata"])
    result["telemetry_complete"] = bool(result["telemetry_complete"])
    result["simulator"] = result["metadata"].get("simulator", result["source"] if result["source"] in ("cooja", "ns3") else None)
    return result

def run_state(row, request):
    result = run_public(row)
    manager = getattr(request.app.state, "ns3_jobs", None)
    job = manager.jobs.get(result["run_id"]) if manager else None
    process = job.get("process") if job else None
    if result["status"] == "running" and process is not None and process.poll() is not None:
        result["status"] = "ingesting"
    return result

def insert_reading(db, r):
    now = datetime.now(timezone.utc).isoformat()
    values = (r.run_id, r.node_id, r.boot_id, r.sequence_number, r.temperature,
              r.timestamp.astimezone(timezone.utc).isoformat(), now, r.sim_time_us, r.payload_bytes)
    cursor = db.execute("""INSERT INTO readings VALUES(?,?,?,?,?,?,?,?,?)
        ON CONFLICT(run_id,node_id,boot_id,sequence_number) DO UPDATE SET
          timestamp=excluded.timestamp, sim_time_us=excluded.sim_time_us
        WHERE excluded.sim_time_us IS NOT NULL AND excluded.sim_time_us < readings.sim_time_us""", values)
    return cursor.rowcount > 0

@router.post("/runs", status_code=201)
def create_run(run: Run, request: Request):
    meta = run.model_dump(mode="json", exclude_none=True)
    if run.simulator is not None and run.simulator != run.source:
        raise HTTPException(422, "Simulator must agree with experiment source")
    with db_for(request) as db:
        old = db.execute("SELECT * FROM runs WHERE run_id=?", (run.run_id,)).fetchone()
        if old:
            if json.loads(old["metadata"]) != meta:
                raise HTTPException(409, "Run ID already exists with different metadata")
            return run_public(old)
        db.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?)", (
            run.run_id, run.name, run.source, run.started_at.astimezone(timezone.utc).isoformat(),
            run.duration_s, run.nodes, "running", int(run.telemetry_complete), json.dumps(meta)))
        return run_public(resolve_run(db, run.run_id))

@router.get("/runs")
def runs(request: Request):
    with db_for(request) as db:
        return [run_state(r, request) for r in db.execute("SELECT * FROM runs ORDER BY started_at DESC")]

@router.post("/runs/{run_id}/complete")
def complete(run_id: str, request: Request):
    with db_for(request) as db:
        run = resolve_run(db, run_id)
        db.execute("UPDATE runs SET status='completed' WHERE run_id=?", (run_id,))
        return {"run_id": run_id, "status": "completed"}

@router.post("/runs/{run_id}/events")
def ingest_events(run_id: str, events: Annotated[list[Event], Body(min_length=1, max_length=500)], request: Request):
    inserted = 0
    with db_for(request) as db:
        run = resolve_run(db, run_id)
        start = datetime.fromisoformat(run["started_at"])
        for event in events:
            if event.node_id > run["nodes"] or event.sim_time_us > run["duration_s"] * 1e6:
                raise HTTPException(422, "Event outside configured node/time bounds")
            if any(n > run["nodes"] for n in (event.path or []) + [n for n in (event.forwarding_node, event.next_hop) if n is not None]):
                raise HTTPException(422, "Packet path exceeds configured nodes")
            payload = json.dumps(event.model_dump(exclude_none=True), sort_keys=True)
            old = db.execute("SELECT payload FROM events WHERE run_id=? AND event_id=?", (run_id, event.event_id)).fetchone()
            if old and old["payload"] != payload:
                raise HTTPException(409, "Event ID reused with different contents")
            cursor = db.execute("INSERT OR IGNORE INTO events VALUES(?,?,?,?,?,?)", (
                run_id, event.event_id, event.type, event.node_id, event.sim_time_us, payload))
            inserted += cursor.rowcount
            if event.type == "rx":
                insert_reading(db, Reading(run_id=run_id, node_id=event.node_id, boot_id=event.boot_id,
                    sequence_number=event.sequence_number, temperature=event.temperature_centi / 100,
                    timestamp=start + timedelta(microseconds=event.sim_time_us),
                    sim_time_us=event.sim_time_us, payload_bytes=event.payload_bytes))
    return {"accepted": len(events), "inserted": inserted}

@router.post("/readings", status_code=201)
def post_reading(reading: Reading, request: Request):
    with db_for(request) as db:
        if reading.run_id == "manual" and not db.execute("SELECT 1 FROM runs WHERE run_id='manual'").fetchone():
            run = Run(run_id="manual", name="Direct sensor ingestion", source="manual", nodes=32,
                      duration_s=604800, started_at=datetime.now(timezone.utc))
            db.execute("INSERT INTO runs VALUES(?,?,?,?,?,?,?,?,?)", (
                run.run_id, run.name, run.source, run.started_at.isoformat(), run.duration_s,
                run.nodes, "running", 0, run.model_dump_json()))
        run = resolve_run(db, reading.run_id)
        if run["telemetry_complete"]:
            raise HTTPException(409, "Measured experiments require /events ingestion to preserve TX/RX evidence")
        if reading.node_id > run["nodes"]:
            raise HTTPException(422, "Node exceeds configured experiment")
        inserted = insert_reading(db, reading)
    return {"status": "stored" if inserted else "duplicate", **reading.model_dump(mode="json")}

@router.get("/readings")
def readings(request: Request, run_id: str | None = None, node_id: int | None = Query(None, ge=1, le=32),
             limit: int = Query(1000, ge=1, le=10000), offset: int = Query(0, ge=0),
             since: datetime | None = None, until: datetime | None = None):
    with db_for(request) as db:
        run = resolve_run(db, run_id)
        where, params = ["run_id=?"], [run["run_id"]]
        if node_id is not None: where.append("node_id=?"); params.append(node_id)
        for op, value in [(">=", since), ("<=", until)]:
            if value:
                if value.tzinfo is None: raise HTTPException(422, "Dates require a timezone")
                where.append(f"timestamp {op} ?"); params.append(value.astimezone(timezone.utc).isoformat())
        sql = " AND ".join(where)
        total = db.execute("SELECT COUNT(*) FROM readings WHERE " + sql, params).fetchone()[0]
        rows = db.execute("SELECT * FROM readings WHERE " + sql + " ORDER BY timestamp DESC,node_id LIMIT ? OFFSET ?", params + [limit, offset])
        return {"items": [dict(r) for r in rows], "total": total, "limit": limit, "offset": offset}

@router.get("/readings/latest")
def latest(request: Request, run_id: str | None = None):
    with db_for(request) as db:
        run = resolve_run(db, run_id)
        rows = db.execute("""SELECT * FROM (SELECT *, ROW_NUMBER() OVER
            (PARTITION BY node_id ORDER BY timestamp DESC,sequence_number DESC) AS rn
            FROM readings WHERE run_id=?) WHERE rn=1 ORDER BY node_id""", (run["run_id"],))
        return [{k: r[k] for k in r.keys() if k != "rn"} for r in rows]

def snapshot(request, run_id=None):
    with db_for(request) as db:
        db.execute("BEGIN")
        run = resolve_run(db, run_id)
        events = [json.loads(r[0]) for r in db.execute("SELECT payload FROM events WHERE run_id=? ORDER BY sim_time_us,rowid", (run["run_id"],))]
        rows = [dict(r) for r in db.execute("SELECT * FROM readings WHERE run_id=?", (run["run_id"],))]
    visible_run = run_state(run, request)
    metrics = summarize(dict(run, status=visible_run["status"]), events, rows)
    return {"run": visible_run, "packet_events": [e for e in events if e["type"] in ("tx", "rx", "forward")][-40:], **metrics}

@router.get("/dashboard")
def dashboard(request: Request, run_id: str | None = None):
    return snapshot(request, run_id)

@router.get("/nodes")
def nodes(request: Request, run_id: str | None = None):
    return snapshot(request, run_id)["nodes"]

@router.get("/network/statistics")
def statistics(request: Request, run_id: str | None = None):
    return snapshot(request, run_id)["statistics"]

@router.get("/network/health")
def health(request: Request, run_id: str | None = None):
    s = snapshot(request, run_id)["statistics"]
    return {k: s[k] for k in ["run_id", "run_status", "health", "active_nodes", "total_nodes", "pdr", "metric_basis"]}

@router.get("/export/readings.csv")
def export(request: Request, run_id: str | None = None):
    with db_for(request) as db:
        run = resolve_run(db, run_id)
        rows = db.execute("SELECT * FROM readings WHERE run_id=? ORDER BY timestamp,node_id", (run["run_id"],))
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([col[0] for col in rows.description])
        writer.writerows(rows)
    return Response(output.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="readings.csv"'})


@router.get("/runs/{run_id}/events")
def event_history(run_id: str, request: Request, offset: int = Query(0, ge=0), limit: int = Query(200, ge=1, le=1000)):
    with db_for(request) as db:
        resolve_run(db, run_id)
        total = db.execute("SELECT COUNT(*) FROM events WHERE run_id=?", (run_id,)).fetchone()[0]
        rows = db.execute("SELECT payload FROM events WHERE run_id=? ORDER BY sim_time_us,event_id LIMIT ? OFFSET ?", (run_id, limit, offset))
        return {"items": [json.loads(r[0]) for r in rows], "total": total, "offset": offset, "limit": limit}

@router.get("/comparison")
def comparison(request: Request, cooja: str, ns3: str):
    left, right = snapshot(request, cooja), snapshot(request, ns3)
    if left["run"]["source"] != "cooja" or right["run"]["source"] != "ns3":
        raise HTTPException(422, "Select one Cooja run and one NS-3 run")
    return {"cooja": left, "ns3": right, "notice": "Different simulator, propagation, MAC, routing and energy models; this is a descriptive comparison, not a controlled equivalence claim."}
