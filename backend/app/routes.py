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
    meta = run.model_dump(mode="json")
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
        return [run_public(r) for r in db.execute("SELECT * FROM runs ORDER BY started_at DESC")]

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
        events = [json.loads(r[0]) for r in db.execute("SELECT payload FROM events WHERE run_id=?", (run["run_id"],))]
        rows = [dict(r) for r in db.execute("SELECT * FROM readings WHERE run_id=?", (run["run_id"],))]
    return {"run": run_public(run), **summarize(run, events, rows)}

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
