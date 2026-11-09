#!/usr/bin/env python3
"""Analyze actual Cooja logs without a running server; export CSV/JSON/PNG evidence."""
import argparse
import csv
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".runtime" / "cache"))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".runtime" / "matplotlib"))
from backend.app.services import summarize, key
from scripts.bridge import parse_line

def load_experiment(directory):
    directory = Path(directory)
    run = json.loads((directory / "manifest.json").read_text())
    run["status"] = "running"
    events, rows = [], {}
    end = None
    logfile = directory / "COOJA.testlog"
    with logfile.open() as f:
        for line_no, line in enumerate(f, 1):
            if "WSN_META " in line: end = json.loads(line.split("WSN_META ", 1)[1])
            event = parse_line(line, line_no)
            if event:
                events.append(event)
                if event["type"] == "rx":
                    timestamp = datetime.fromisoformat(run["started_at"]) + timedelta(microseconds=event["sim_time_us"])
                    rows.setdefault(key(event), {"run_id": run["run_id"], "node_id": event["node_id"],
                        "boot_id": event["boot_id"], "sequence_number": event["sequence_number"],
                        "temperature": event["temperature_centi"] / 100, "timestamp": timestamp.isoformat(),
                        "received_at": timestamp.isoformat(), "sim_time_us": event["sim_time_us"],
                        "payload_bytes": event["payload_bytes"]})
    if end: run["status"] = "completed"
    run["validation"] = end
    return run, events, list(rows.values())

def write_csv(path, rows, fields=None):
    rows = list(rows)
    if fields is None: fields = list(dict.fromkeys(k for row in rows for k in row))
    with Path(path).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)

def analyze(directory, graphs=True):
    directory = Path(directory)
    run, events, readings = load_experiment(directory)
    if not run["validation"]:
        raise ValueError(f"{directory}: incomplete run (no end marker). Refusing to publish final metrics.")
    result = summarize(run, events, readings)
    result["experiment"] = run
    stats = result["statistics"]
    (directory / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    write_csv(directory / "readings.csv", readings)
    write_csv(directory / "events.csv", events)
    write_csv(directory / "nodes.csv", result["nodes"])
    write_csv(directory / "metrics.csv", [{k:v for k,v in stats.items() if not isinstance(v,dict)}])
    if graphs: plot(directory, run, events, readings, result)
    return result

def plot(directory, run, events, readings, result):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "figure.facecolor": "white"})
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    nodes = result["nodes"]
    for n in nodes:
        history = sorted([r for r in readings if r["node_id"] == n["node_id"]], key=lambda r:r["sim_time_us"])
        axes[0,0].plot([r["sim_time_us"] / 1e6 for r in history], [r["temperature"] for r in history], label=f"Node {n['node_id']}", lw=1.4)
    axes[0,0].set(title="Temperature readings received at sink", xlabel="Simulation time (s)", ylabel="Temperature (°C)")
    axes[0,0].legend(ncol=2, fontsize=7)
    ids=[n["node_id"] for n in nodes]
    axes[0,1].bar(ids, [n["pdr"] or 0 for n in nodes], color="#269a77")
    axes[0,1].set(title="Application packet delivery ratio", xlabel="Logical node ID", ylabel="PDR (%)", ylim=(0,105), xticks=ids)
    tx={}
    for e in events:
        if e["type"]=="tx": tx.setdefault(key(e), e)
    delays=[(r["sim_time_us"]-tx[key(r)]["sim_time_us"])/1000 for r in readings if key(r) in tx]
    axes[1,0].hist(delays, bins=20, color="#5d80c7", edgecolor="white")
    axes[1,0].set(title="Measured end-to-end delay", xlabel="First TX → first RX (ms)", ylabel="Packets")
    axes[1,1].bar(ids, [n["energy_j"] or 0 for n in nodes], color="#c69545")
    axes[1,1].set(title="Estimated energy from Energest", xlabel="Logical node ID", ylabel="Estimated energy (J)", xticks=ids)
    fig.suptitle(f"{run['nodes']}-sensor Cooja experiment · seed {run['seed']} · {run['duration_s']} s", fontsize=15)
    fig.savefig(directory / "performance.png", dpi=180)
    fig.savefig(directory / "performance.svg")
    plt.close(fig)

if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory", type=Path)
    p.add_argument("--no-graphs", action="store_true")
    args=p.parse_args()
    result=analyze(args.directory, not args.no_graphs)
    print(json.dumps(result["statistics"], indent=2))
