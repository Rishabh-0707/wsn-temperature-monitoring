#!/usr/bin/env python3
"""Generate portable, headless-testable Cooja configurations from topology parameters."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
INTERFACES = ["interfaces.Position", "contikimote.interfaces.ContikiMoteID",
              "contikimote.interfaces.ContikiRS232", "interfaces.RimeAddress",
              "contikimote.interfaces.ContikiIPAddress", "contikimote.interfaces.ContikiRadio",
              "contikimote.interfaces.ContikiClock", "contikimote.interfaces.ContikiLED",
              "interfaces.Mote2MoteRelations", "interfaces.MoteAttributes"]

def generate(nodes=5, duration=300, radio_range=50, seed=123456, success=1.0, speed=None, suffix=""):
    if nodes not in range(1, 33) or duration < 30 or radio_range <= 0 or not 0 < success <= 1:
        raise ValueError("nodes 1..32, duration >=30, positive range, success in (0,1]")
    root = ET.Element("simconf", version="2023090701")
    sim = ET.SubElement(root, "simulation")
    ET.SubElement(sim, "title").text = f"WSN temperature / {nodes} sensors"
    ET.SubElement(sim, "randomseed").text = str(seed)
    if speed is not None:
        if speed <= 0: raise ValueError("Speed must be positive")
        ET.SubElement(sim, "speedlimit").text = str(speed)
    # Global Cooja time and mote clock align; delay uses global TX/RX regardless.
    ET.SubElement(sim, "motedelay_us").text = "0"
    radio = ET.SubElement(sim, "radiomedium")
    radio.text = "org.contikios.cooja.radiomediums.UDGM"
    for key, value in [("transmitting_range", radio_range), ("interference_range", radio_range * 2),
                       ("success_ratio_tx", success), ("success_ratio_rx", 1.0)]:
        ET.SubElement(radio, key).text = str(value)
    for identifier, directory, source in [("wsnsink", "sink-node", "sink_node"),
                                           ("wsnsensor", "temperature-sensor", "temperature_sensor")]:
        mt = ET.SubElement(sim, "motetype")
        mt.text = "org.contikios.cooja.contikimote.ContikiMoteType"
        ET.SubElement(mt, "identifier").text = identifier
        ET.SubElement(mt, "description").text = source
        ET.SubElement(mt, "source").text = f"[CONFIG_DIR]/../{directory}/{source}.c"
        ET.SubElement(mt, "commands").text = f"$(MAKE) -j1 {source}.cooja TARGET=cooja"
        for interface in INTERFACES:
            ET.SubElement(mt, "moteinterface").text = "org.contikios.cooja." + interface
    topology = []
    for mote_id in range(1, nodes + 2):
        i = mote_id - 2
        x, y = (0, 0) if mote_id == 1 else (35 * (i // 2 + 1), 25 * (i % 2))
        topology.append({"mote_id": mote_id, "node_id": mote_id - 1, "x": x, "y": y})
        mote = ET.SubElement(sim, "mote")
        pos = ET.SubElement(mote, "interface_config")
        pos.text = "org.contikios.cooja.interfaces.Position"
        for key, value in [("x", x), ("y", y), ("z", 0)]:
            ET.SubElement(pos, key).text = str(value)
        identity = ET.SubElement(mote, "interface_config")
        identity.text = "org.contikios.cooja.contikimote.interfaces.ContikiMoteID"
        ET.SubElement(identity, "id").text = str(mote_id)
        ET.SubElement(mote, "motetype_identifier").text = "wsnsink" if mote_id == 1 else "wsnsensor"
    plugin = ET.SubElement(root, "plugin")
    plugin.text = "org.contikios.cooja.plugins.ScriptRunner"
    config = ET.SubElement(plugin, "plugin_config")
    pacing = f"sim.setSpeedLimit({speed});\n" if speed is not None else ""
    ET.SubElement(config, "script").text = pacing + f'''wsnSeen = {{}};
wsnMultihop = false;
wsnFinish = function() {{
  log.log('WSN_META ' + JSON.stringify({{type:'end', sim_time_us:{duration * 1000000}, received_nodes:Object.keys(wsnSeen).length, multihop:wsnMultihop}}) + '\\n');
  if(Object.keys(wsnSeen).length == {nodes} && wsnMultihop) log.testOK(); else log.testFailed();
}};
TIMEOUT({duration * 1000}, wsnFinish());
while(true) {{
  var line = String(msg);
  log.log('WSN_EVENT ' + JSON.stringify({{sim_time_us:time, mote_id:id, message:line}}) + '\\n');
  if(line.charAt(0) == '{{') {{
    try {{
      var event = JSON.parse(line);
      if(event.type == 'rx') wsnSeen[event.node_id] = true;
      if(event.type == 'status' && event.node_id > 0 && event.parent_mote_id > 1 && event.parent_mote_id != 65535) wsnMultihop = true;
    }} catch(e) {{ log.log('PARSE_ERROR ' + line + '\\n'); }}
  }}
  YIELD();
}}'''
    ET.SubElement(config, "active").text = "true"
    out = ROOT / "contiki" / "simulations"
    out.mkdir(parents=True, exist_ok=True)
    ET.indent(root)
    if suffix and not suffix.replace('_', '').isalnum(): raise ValueError("Suffix must be alphanumeric")
    path = out / f"wsn_{nodes}_nodes{('_' + suffix) if suffix else ''}.csc"
    ET.ElementTree(root).write(path, encoding="UTF-8", xml_declaration=True)
    meta = {"nodes": nodes, "duration_s": duration, "radio_range_m": radio_range,
            "seed": seed, "success_ratio_tx": success, "speed_limit": speed, "topology": topology}
    path.with_suffix(".json").write_text(json.dumps(meta, indent=2) + "\n")
    print(path)

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--nodes", type=int, nargs="+", default=[5, 10])
    p.add_argument("--duration", type=int, default=300)
    p.add_argument("--range", type=float, default=50)
    p.add_argument("--seed", type=int, default=123456)
    p.add_argument("--success", type=float, default=1)
    p.add_argument("--speed", type=float, help="Simulation seconds per real second; omit for fastest execution")
    p.add_argument("--suffix", default="", help="Save a variant without replacing baseline configurations")
    a = p.parse_args()
    for n in a.nodes:
        generate(n, a.duration, a.range, a.seed, a.success, a.speed, a.suffix)
