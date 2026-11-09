#!/usr/bin/env python3
"""Forward actual Cooja serial events to FastAPI; supports finite import or live tail."""
import argparse
import hashlib
import json
import logging
from pathlib import Path
import re
import time
import httpx

LOG = logging.getLogger("wsn.bridge")
CONTROL = re.compile(r"sending a (?:[a-z]+-)?(DIS|DIO|DAO)(?:-(ACK|NACK))?\b")

def parse_line(line, line_number):
    if "WSN_EVENT " not in line:
        return None
    envelope = json.loads(line.split("WSN_EVENT ", 1)[1])
    message = envelope["message"].strip()
    if message.startswith("{"):
        event = json.loads(message)
    elif match := CONTROL.search(message):
        event = {"type": "control", "node_id": envelope["mote_id"] - 1,
                 "control_kind": "DAO-ACK" if match.group(2) else match.group(1)}
    else:
        return None
    event["sim_time_us"] = int(envelope["sim_time_us"])
    event["event_id"] = hashlib.sha256(f"{line_number}:{line.strip()}".encode()).hexdigest()
    return event

def post(client, path, body=None):
    for attempt in range(6):
        try:
            response = client.post(path, json=body)
            response.raise_for_status()
            return response.json()
        except (httpx.TransportError, httpx.HTTPStatusError) as error:
            if isinstance(error, httpx.HTTPStatusError) and error.response.status_code < 500:
                raise RuntimeError(error.response.text) from error
            if attempt == 5: raise
            LOG.warning("Backend unavailable; retry %s", attempt + 1)
            time.sleep(min(2 ** attempt, 10))

def import_log(logfile, manifest, url, follow=False, idle_timeout=30):
    meta = json.loads(Path(manifest).read_text())
    total = 0
    completed = False
    with httpx.Client(base_url=url, timeout=30) as client:
        post(client, "/api/runs", meta)
        with Path(logfile).open() as stream:
            batch, line_no, partial = [], 0, ""
            last_activity = time.monotonic()
            while True:
                line = stream.readline()
                if line:
                    last_activity = time.monotonic()
                if line and not line.endswith("\n") and follow:
                    partial += line
                    time.sleep(0.05)
                    continue
                if line:
                    line = partial + line
                    partial = ""
                    line_no += 1
                    if "WSN_META " in line:
                        end = json.loads(line.split("WSN_META ", 1)[1])
                        completed = end.get("type") == "end"
                    event = parse_line(line, line_no)
                    if event: batch.append(event)
                if batch and (len(batch) >= 200 or not line):
                    result = post(client, f"/api/runs/{meta['run_id']}/events", batch)
                    total += result["inserted"]
                    LOG.info("Imported %d new events", total)
                    batch = []
                if not line:
                    if completed or not follow: break
                    if time.monotonic() - last_activity > idle_timeout:
                        raise TimeoutError(f"No simulator output for {idle_timeout} seconds; log remains available for replay")
                    time.sleep(0.25)
        if completed:
            post(client, f"/api/runs/{meta['run_id']}/complete")
    return {"inserted": total, "completed": completed, "run_id": meta["run_id"]}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("logfile", type=Path)
    p.add_argument("--manifest", type=Path)
    p.add_argument("--url", default="http://127.0.0.1:8001")
    p.add_argument("--follow", action="store_true")
    p.add_argument("--idle-timeout", type=float, default=30)
    args = p.parse_args()
    if args.idle_timeout <= 0: p.error("--idle-timeout must be positive")
    print(json.dumps(import_log(args.logfile, args.manifest or args.logfile.parent / "manifest.json", args.url, args.follow, args.idle_timeout)))
