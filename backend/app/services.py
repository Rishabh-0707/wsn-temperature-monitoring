"""Pure metric calculations shared by the API and offline analysis."""
from collections import defaultdict
from datetime import datetime, timezone
from statistics import mean

ENERGY_MODEL = {"voltage_v": 3.0, "cpu_ma": 1.8, "lpm_ma": 0.005,
                "deep_lpm_ma": 0.001, "transmit_ma": 17.4, "listen_ma": 18.8,
                "battery_mah": 2000, "label": "Illustrative MCU + radio model; not board calibration"}

def key(e):
    return e["node_id"], e.get("boot_id", 0), e["sequence_number"]

def summarize(run, events, readings, now=None, energy_model=None):
    model = dict(ENERGY_MODEL, **(energy_model or {}))
    events = sorted(events, key=lambda e: e["sim_time_us"])
    tx, rx, statuses, energies = {}, {}, {}, {}
    received_hops = {}
    counts = defaultdict(int)
    for e in events:
        counts[e["type"]] += 1
        if e["type"] == "tx": tx.setdefault(key(e), e)
        if e["type"] == "rx" and e.get("hop_count") is not None: received_hops.setdefault(key(e), e["hop_count"])
        if e["type"] == "status": statuses[e["node_id"]] = e
        if e["type"] == "energy": energies[(e["node_id"], e.get("boot_id", 0))] = e
    for r in sorted(readings, key=lambda r: r["timestamp"]): rx.setdefault(key(r), r)
    measured = bool(run["telemetry_complete"])
    elapsed_us = max([e["sim_time_us"] for e in events] + [0])
    duration = run["duration_s"] if run["status"] == "completed" else elapsed_us / 1e6
    delivered = tx.keys() & rx.keys()
    missing = tx.keys() - rx.keys()
    delays = [(rx[k]["sim_time_us"] - tx[k]["sim_time_us"]) / 1000 for k in delivered
              if rx[k]["sim_time_us"] is not None and rx[k]["sim_time_us"] >= tx[k]["sim_time_us"]]
    per_node_energy = defaultdict(float)
    per_node_seconds = defaultdict(float)
    for (node, boot), e in energies.items():
        hz = e["ticks_per_second"]
        joules = model["voltage_v"] * sum(e[state] / hz * model[state + "_ma"] / 1000
                                          for state in ["cpu", "lpm", "deep_lpm", "transmit", "listen"])
        per_node_energy[node] += joules
        per_node_seconds[node] += (e["cpu"] + e["lpm"] + e["deep_lpm"]) / hz
    nodes = []
    latest = {}
    for r in sorted(readings, key=lambda r: r["timestamp"]): latest[r["node_id"]] = r
    now = now or datetime.now(timezone.utc)
    for node in sorted(set(range(1, run["nodes"] + 1)) | set(latest)):
        history = [r for r in rx.values() if r["node_id"] == node]
        boots = defaultdict(set)
        for r in history: boots[r["boot_id"]].add(r["sequence_number"])
        gaps = sum(max(seqs) - len(seqs) for seqs in boots.values())
        last = latest.get(node)
        if last and run["source"] in ("cooja", "ns3") and last["sim_time_us"] is not None:
            age = max(0, (duration * 1e6 - last["sim_time_us"]) / 1e6)
        elif last:
            age = max(0, (now - datetime.fromisoformat(last["received_at"])).total_seconds())
        else: age = None
        energy = per_node_energy.get(node)
        seconds = per_node_seconds.get(node, 0)
        lifetime = (model["battery_mah"] / 1000 * model["voltage_v"] * 3600 / (energy / seconds) / 3600
                    if energy and seconds else None)
        sent = sum(k[0] == node for k in tx)
        received = len(history)
        lost = sum(k[0] == node for k in missing) if measured else None
        nodes.append({"node_id": node, "temperature": last["temperature"] if last else None,
                      "last_received": last["timestamp"] if last else None,
                      "status": "active" if age is not None and age <= 15 else "offline",
                      "packets_sent": sent if measured else None, "packets_received": received,
                      "packets_lost": lost, "sequence_gaps": gaps,
                      "pdr": 100 * sum(k[0] == node for k in delivered) / sent if measured and sent else None,
                      "parent_mote_id": statuses.get(node, {}).get("parent_mote_id"),
                      "rank": statuses.get(node, {}).get("rank"), "energy_j": energy,
                      "energy_observed_seconds": seconds, "lifetime_hours": lifetime,
                      "remaining_energy_j": max(0,model["battery_mah"]/1000*model["voltage_v"]*3600-energy) if energy is not None else None})
    temps = [r["temperature"] for r in latest.values()]
    pdr = 100 * len(delivered) / len(tx) if measured and tx else None
    active = sum(n["status"] == "active" for n in nodes)
    stats = {"run_id": run["run_id"], "source": run["source"], "run_status": run["status"],
             "total_nodes": len(nodes), "active_nodes": active,
             "average_temperature": mean(temps) if temps else None,
             "min_temperature": min(temps) if temps else None, "max_temperature": max(temps) if temps else None,
             "historical_min_temperature": min((r["temperature"] for r in readings), default=None),
             "historical_max_temperature": max((r["temperature"] for r in readings), default=None),
             "packets_sent": len(tx) if measured else None, "packets_received": len(rx),
             "packets_lost": len(missing) if measured else None, "pdr": pdr,
             "packet_loss_ratio": 100 - pdr if pdr is not None else None,
             "transmission_attempts": counts["tx"] if measured else None,
             "retry_attempts": counts["tx"] - len(tx) if measured else None,
             "duplicate_receptions": max(0, counts["rx"] - len(rx)),
             "unmatched_receptions": len(rx.keys() - tx.keys()),
             "average_hop_count": mean(received_hops.values()) if received_hops else None,
             "sampling_success_ratio": 100*len(rx)/counts["sample"] if counts["sample"] else None,
             "generated_samples": counts["sample"] if measured else None,
             "no_route_samples": counts["no_route"] if measured else None,
             "failed_ack_samples": counts["failed"] if measured else None,
             "sequence_gaps": sum(n["sequence_gaps"] for n in nodes),
             "average_delay_ms": mean(delays) if delays else None,
             "delay_sample_count": len(delays), "duration_s": duration,
             "throughput_bps": sum(r["payload_bytes"] * 8 for r in rx.values()) / duration if duration else None,
             "routing_control_packets": counts["control"] if measured else None,
             "routing_overhead_per_data_packet": counts["control"] / len(tx) if measured and tx else None,
             "estimated_energy_j": sum(per_node_energy.values()) if energies else None,
             "estimated_network_lifetime_hours": min((n["lifetime_hours"] for n in nodes if n["lifetime_hours"]), default=None),
             "energy_model": model, "metric_basis": "measured TX/RX events" if measured else "receive-only; sent/PDR unavailable",
             "health": "healthy" if active == len(nodes) and pdr is not None and pdr >= 95 else "degraded" if active else "offline"}
    return {"statistics": stats, "nodes": nodes}
