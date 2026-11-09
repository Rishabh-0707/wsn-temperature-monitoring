import { Radio } from "lucide-react";
export default function Topology({ run, nodes, selected, onSelect }) {
  const positions = run.metadata.topology || [];
  const lookup = Object.fromEntries(positions.map((p) => [p.mote_id, p]));
  const maxX = Math.max(100, ...positions.map((p) => p.x));
  const point = (p) => ({
    x: 35 + (p.x / maxX) * 355,
    y: p.mote_id === 1 ? 112 : 65 + p.y * 3.8,
  });
  if (!positions.length)
    return (
      <div className="empty compact">
        Topology is unavailable for direct sensor ingestion.
      </div>
    );
  return (
    <div className="topology-wrap">
      <svg
        viewBox="0 0 430 225"
        role="img"
        aria-label="Observed RPL parent links and node positions"
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
          RPL-Lite
        </span>
      </div>
    </div>
  );
}
