#!/usr/bin/env python3
"""Compare independently executed experiments; never substitute synthetic data."""
import argparse
import json
from pathlib import Path
from performance_analysis import analyze, write_csv

def compare(directories, output):
    output.mkdir(parents=True, exist_ok=True)
    rows=[]
    for directory in directories:
        result=analyze(directory)
        s=result["statistics"]
        rows.append({"sensor_nodes":s["total_nodes"], **{k:s[k] for k in ["packets_sent","packets_received","packets_lost","pdr","packet_loss_ratio","average_delay_ms","throughput_bps","estimated_energy_j","estimated_network_lifetime_hours","routing_control_packets","routing_overhead_per_data_packet","no_route_samples"]}})
    write_csv(output / "comparison.csv", rows)
    (output / "comparison.json").write_text(json.dumps(rows, indent=2)+"\n")
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(12,3.6),constrained_layout=True)
    labels=[str(r["sensor_nodes"]) for r in rows]
    for ax, key, title, unit in zip(axes,["pdr","average_delay_ms","routing_control_packets"],["Delivery ratio","End-to-end delay","RPL control output"],["%","ms","packets"]):
        ax.bar(range(len(rows)),[r[key] or 0 for r in rows],color=["#269a77","#5d80c7"]*(len(rows)//2+1))
        ax.set(title=title,xticks=range(len(rows)),xticklabels=labels,xlabel="Sensor nodes",ylabel=unit)
        ax.spines[['right','top']].set_visible(False)
    fig.savefig(output/"comparison.png",dpi=180);plt.close(fig)
    return rows

if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("directories",nargs="+",type=Path);p.add_argument("--output",type=Path,default=Path("analysis/results"))
    a=p.parse_args();print(json.dumps(compare(a.directories,a.output),indent=2))
