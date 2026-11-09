import os
import sqlite3
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "wsn.sqlite3"

def connect(path=None):
    path = Path(path or os.environ.get("WSN_DB", DEFAULT_DB))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def initialize(path=None):
    with connect(path) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS runs (
          run_id TEXT PRIMARY KEY, name TEXT NOT NULL, source TEXT NOT NULL,
          started_at TEXT NOT NULL, duration_s REAL NOT NULL,
          nodes INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'running',
          telemetry_complete INTEGER NOT NULL, metadata TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events (
          run_id TEXT NOT NULL REFERENCES runs(run_id), event_id TEXT NOT NULL,
          type TEXT NOT NULL, node_id INTEGER NOT NULL, sim_time_us INTEGER NOT NULL,
          payload TEXT NOT NULL, PRIMARY KEY(run_id, event_id)
        );
        CREATE INDEX IF NOT EXISTS event_time ON events(run_id, sim_time_us);
        CREATE TABLE IF NOT EXISTS readings (
          run_id TEXT NOT NULL REFERENCES runs(run_id), node_id INTEGER NOT NULL,
          boot_id INTEGER NOT NULL, sequence_number INTEGER NOT NULL,
          temperature REAL NOT NULL, timestamp TEXT NOT NULL, received_at TEXT NOT NULL,
          sim_time_us INTEGER, payload_bytes INTEGER NOT NULL,
          PRIMARY KEY(run_id, node_id, boot_id, sequence_number)
        );
        CREATE INDEX IF NOT EXISTS reading_time ON readings(run_id, timestamp);
        """)
