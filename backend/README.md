# FastAPI telemetry backend

From the repository root:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8001
```

`WSN_DB` selects a SQLite file (default `data/wsn.sqlite3`). WAL mode, foreign keys, a 30-second busy timeout, and transaction rollback protect multi-request ingestion. `WSN_CORS_ORIGINS` is a comma-separated list; the default allows the local Vite frontend. The built frontend is served at `/` when `frontend/dist` exists at process start.

## API

| Method/path | Behavior |
|---|---|
| `POST /api/readings` | Validate and store one direct/manual reading; deduplicate by run/node/boot/sequence |
| `GET /api/readings` | Newest-first history; `run_id`, `node_id`, `since`, `until`, `offset`, `limit` (max 10,000) |
| `GET /api/readings/latest` | Most recent reading per node in one experiment |
| `GET /api/nodes` | Availability, latest reading, delivery counters, sequence gaps and parent |
| `GET /api/network/statistics` | Delivery, delay, throughput, routing and energy estimates |
| `GET /api/network/health` | Experiment status and connectivity summary |
| `POST /api/runs` / `GET /api/runs` | Register/list isolated experiments with explicit start epoch and provenance |
| `POST /api/runs/{id}/events` | Atomically ingest 1–500 timestamped TX/RX/control/Energest/status events |
| `POST /api/runs/{id}/complete` | Mark observation window complete |
| `GET /api/dashboard` | Consistent snapshot of run, node list and calculated statistics |
| `GET /api/export/readings.csv` | All unique readings for the selected run |
| `GET /healthz` | Process liveness |

Omitting `run_id` on a GET selects the newest experiment. No experiments returns a descriptive 404. The frontend handles this with an empty state. API schemas and examples are available at `/docs`.

```json
{"node_id":1,"temperature":28.5,"sequence_number":102,"timestamp":"2026-11-09T10:30:00Z"}
```

This minimal reading is accepted into the `manual` experiment. For a hardware deployment, register an explicitly named run with the known node count, and include `run_id` and a boot identifier. Direct readings do not establish total transmitted packets; PDR and packet loss remain null. Measured Cooja runs accept `/events` only to preserve their TX/RX evidence.

The current research-sized implementation calculates metrics from an experiment's events in memory. Use incremental aggregates, retention and authentication before turning it into a high-volume production service. History display is capped at 10,000 readings per request; CSV export includes all retained readings.
