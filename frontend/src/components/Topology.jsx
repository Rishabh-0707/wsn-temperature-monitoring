import { Radio } from "lucide-react";
export default function Topology({ run, nodes, selected, onSelect, events = [] }) {
  const positions = run.metadata.topology || [];
  const lookup = Object.fromEntries(positions.map((p) => [p.mote_id, p]));
  const minX = Math.min(0, ...positions.map(p=>p.x));
  const maxX = Math.max(100, ...positions.map(p=>p.x));
  const minY = Math.min(0, ...positions.map(p=>p.y));
  const maxY = Math.max(25, ...positions.map(p=>p.y));
  const point = (p) => ({
    x: run.source === "ns3" ? 35 + ((p.x-minX) / (maxX-minX)) * 355 : 35 + (p.x/maxX)*355,
    y: run.source === "ns3" ? 45 + ((p.y-minY) / (maxY-minY))*105 : p.mote_id === 1 ? 112 : 65+p.y*3.8,
  });
  if (!positions.length)
    return (
      <div className="empty compact">
        Topology is unavailable for direct sensor ingestion.
      </div>
    );
  const recent = [...events].reverse().find(e => e.type === "rx" && e.path?.length > 1);
  const trail = recent?.path.map(id=>lookup[id+1]).filter(Boolean).map(p=>{const c=point(p);return `${c.x},${c.y}`;}).join(" ");
  return (
    <div className="topology-wrap">
      <svg
        viewBox="0 0 430 225"
        role="img"
        aria-label="Network routes and node positions"
      >
        <defs>
          <pattern
            id="dots"
            width="16"
            height="16"
            patternUnits="userSpaceOnUse"
          >
            <circle cx="1" cy="1" r=".7" fill="var(--border)" />
          </pattern>
        </defs>
        <rect width="430" height="225" fill="url(#dots)" />
        {nodes.map((n) => {
          const a = lookup[n.node_id + 1],
            b = lookup[n.parent_mote_id];
          if (!a || !b) return null;
          const p = point(a),
            q = point(b);
          return (
            <line
              key={n.node_id}
              x1={p.x}
              y1={p.y}
              x2={q.x}
              y2={q.y}
              stroke="var(--accent)"
              strokeOpacity=".55"
              strokeDasharray="4 5"
              strokeWidth="1.5"
            />
          );
        })}
        {trail && <polyline key={recent.event_id} points={trail} fill="none" stroke="var(--accent)" strokeWidth="3" opacity=".7"><title>Recorded path for node {recent.node_id}, packet {recent.sequence_number}</title>{run.status === "running" && <animate attributeName="opacity" values="1;.25;1" dur="1s" repeatCount="2"/>}</polyline>}
        {trail && run.status === "running" && <circle key={`packet-${recent.event_id}`} r="4" fill="var(--text)"><title>Playback of recorded packet path, slowed for visibility</title><animateMotion path={`M ${trail.replaceAll(" ", " L ")}`} dur="1.5s" repeatCount="1" fill="freeze"/></circle>}
        {positions.map((p) => {
          const c = point(p),
            n = nodes.find((n) => n.node_id === p.node_id),
            sink = p.mote_id === 1;
          return (
            <g
              key={p.mote_id}
              className={sink ? "" : "topology-node"}
              tabIndex={sink ? undefined : 0}
              role={sink ? undefined : "button"}
              aria-label={sink ? "Sink" : `Select node ${p.node_id}`}
              onClick={() => !sink && onSelect(String(p.node_id))}
              onKeyDown={(e) => {
                if (!sink && ["Enter", " "].includes(e.key)) {
                  e.preventDefault();
                  onSelect(String(p.node_id));
                }
              }}
            >
              <circle
                cx={c.x}
                cy={c.y}
                r={sink ? 20 : 17}
                fill={sink ? "var(--accent)" : "var(--surface)"}
                stroke={
                  sink || selected === String(p.node_id)
                    ? "var(--accent)"
                    : "var(--border-strong)"
                }
                strokeWidth="2"
              />
              <text
                x={c.x}
                y={c.y + 4}
                textAnchor="middle"
                fontSize="11"
                fontWeight="700"
                fill={sink ? "#073a2a" : "var(--text)"}
              >
                {sink ? "S" : String(p.node_id).padStart(2, "0")}
              </text>
              <text
                x={c.x}
                y={c.y + 33}
                textAnchor="middle"
                fontSize="10"
                fill="var(--muted)"
              >
                {sink
                  ? "SINK"
                  : n?.temperature != null
                    ? `${n.temperature.toFixed(1)}°`
                    : "waiting"}
              </text>
              {!sink && (
                <circle
                  cx={c.x + 13}
                  cy={c.y - 11}
                  r="4"
                  fill={
                    n?.status === "active" ? "var(--accent)" : "var(--muted)"
                  }
                  stroke="var(--surface)"
                  strokeWidth="2"
                />
              )}
            </g>
          );
        })}
      </svg>
      {recent && <p style={{fontSize:12,padding:"0 12px"}}>Latest recorded packet: node {recent.node_id}, sequence {recent.sequence_number}, path {recent.path.join(" → ")}, {(recent.sim_time_us/1e6).toFixed(2)} s.</p>}
      <div className="topology-key">
        <span>
          <i className="dot" />
          Sensor
        </span>
        <span>
          <span className="dashed-line" />
          Observed parent
        </span>
        <span>
          <Radio size={12} />
          {run.source === "ns3" ? "Static IPv6 routes" : "RPL-Lite"}
        </span>
      </div>
    </div>
  );
}
