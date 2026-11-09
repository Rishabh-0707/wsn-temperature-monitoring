#!/usr/bin/env python3
"""Create report figures using project architecture and observed parent links."""
import json
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".runtime/matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".runtime/cache"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle

OUT = ROOT / "docs/figures"
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 10, "font.family": "DejaVu Sans"})

def box(ax, x, y, text, width=2.5, height=.85, color="#eaf4ef"):
    ax.add_patch(FancyBboxPatch((x-width/2,y-height/2),width,height,boxstyle="round,pad=0.04,rounding_size=.08",fc=color,ec="#5c8572",lw=1.2))
    ax.text(x,y,text,ha="center",va="center",fontsize=10,color="#183c2d",linespacing=1.4)

def arrow(ax, a, b, label=None):
    ax.add_patch(FancyArrowPatch(a,b,arrowstyle="-|>",mutation_scale=12,color="#527564",lw=1.2))
    if label:
        ax.text((a[0]+b[0])/2,(a[1]+b[1])/2+.15,label,ha="center",fontsize=8,color="#50665b")

def save(fig, name):
    fig.savefig(OUT / f"{name}.svg", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

def architecture():
    fig,ax=plt.subplots(figsize=(12,5.2));ax.set(xlim=(-.4,11.4),ylim=(-.3,4.4));ax.axis("off")
    boxes=[(1.3,3.3,"Temperature motes\n5 or 10 sensors"),(5.4,3.3,"RPL-Lite network\nIEEE 802.15.4 / 6LoWPAN"),(9.5,3.3,"Sink / DAG root\nUDP receive + ACK"),
           (9.5,1.2,"Cooja serial log\nGlobal simulation time"),(5.4,1.2,"Python bridge + FastAPI\nValidate / deduplicate"),(1.3,1.2,"SQLite + dashboard\nHistory / charts / CSV")]
    for x,y,t in boxes:box(ax,x,y,t,width=2.7)
    arrow(ax,(2.7,3.3),(4,3.3),"18-byte UDP")
    arrow(ax,(6.8,3.3),(8.1,3.3),"Multi-hop")
    arrow(ax,(9.5,2.83),(9.5,1.67))
    arrow(ax,(8.1,1.2),(6.8,1.2),"JSON events")
    arrow(ax,(4,1.2),(2.7,1.2),"HTTP / SQL")
    ax.text(5.5,4.15,"System architecture",ha="center",weight="bold",fontsize=16,color="#183c2d")
    ax.text(5.5,.1,"Sensor TX and sink RX events jointly support measured delivery and delay.",ha="center",fontsize=9,color="#50665b")
    save(fig,"architecture")

def topology():
    result=json.loads((ROOT/"analysis/results/baseline_10/summary.json").read_text())
    positions={p['mote_id']:p for p in result['experiment']['topology']}
    fig,ax=plt.subplots(figsize=(12,4.7))
    ax.add_patch(Circle((0,0),50,fill=False,ec="#9db9a7",ls="--",lw=1.2))
    for n in result['nodes']:
        a=positions[n['node_id']+1];b=positions.get(n['parent_mote_id'])
        if b:
            ax.add_patch(FancyArrowPatch((a['x'],a['y']),(b['x'],b['y']),arrowstyle="-|>",mutation_scale=14,shrinkA=12,shrinkB=12,lw=1.5,color="#568b71"))
    for mote,p in positions.items():
        ax.scatter(p['x'],p['y'],s=420 if mote==1 else 320,fc="#269a77" if mote==1 else "#e9f3ed",edgecolor="#376d53",zorder=3)
        ax.text(p['x'],p['y'],"S" if mote==1 else str(p['node_id']),ha="center",va="center",weight="bold",fontsize=10,color="white" if mote==1 else "#183c2d",zorder=4)
    ax.set(xlim=(-15,195),ylim=(-24,63),xlabel="x position (m)",ylabel="y position (m)",title="Ten-sensor topology: observed RPL parents at simulation end")
    ax.text(0,-18,"Sink",ha="center",fontsize=9)
    ax.text(65,53,"Dashed circle: sink's 50 m transmit range",fontsize=9,color="#50665b")
    ax.spines[['top','right']].set_visible(False);ax.grid(alpha=.12);ax.set_aspect('equal')
    save(fig,"topology")

def flowchart():
    fig,ax=plt.subplots(figsize=(10,8));ax.set(xlim=(0,10),ylim=(0,10));ax.axis('off')
    for x,y,t in [(5,9.2,"Initialize UDP and boot ID"),(5,7.7,"Timer expires → sample\nIncrement sequence"),(5,6.2,"RPL route available?"),(2,4.7,"Log no_route\nWait for next sample"),(7.5,4.7,"Log TX; send UDP\nWait up to 1 s for ACK"),(7.5,3.1,"ACK matches sample?"),(4.5,1.5,"Retry while attempts < 3\nOtherwise log failed"),(8,1.5,"Log acknowledged\nWait for next sample")]:
        box(ax,x,y,t,width=2.9,height=.8)
    arrow(ax,(5,8.75),(5,8.15));arrow(ax,(5,7.25),(5,6.65))
    arrow(ax,(3.5,6.2),(2,5.15),"No");arrow(ax,(6.5,6.2),(7.5,5.15),"Yes")
    arrow(ax,(7.5,4.25),(7.5,3.55));arrow(ax,(6.5,2.65),(4.7,1.95),"No");arrow(ax,(8.3,2.65),(8.3,1.95),"Yes")
    ax.text(5,.35,"The sink validates, logs every reception, and ACKs repeats. SQLite deduplicates readings.",ha='center',fontsize=9,color="#50665b")
    save(fig,"sensor_flow")

if __name__ == '__main__':
    architecture();topology();flowchart();print(OUT)
