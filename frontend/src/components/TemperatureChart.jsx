import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";
export const colors = [
  "#31ba91",
  "#678eea",
  "#d6a252",
  "#b78ddd",
  "#e17a8b",
  "#4fbcc9",
  "#9cae64",
  "#cf8e63",
  "#9eabbc",
  "#d96abb",
];
export default function TemperatureChart({ readings, nodes, selected, range }) {
  const sorted = [...readings].sort(
    (a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp),
  );
  const simulated =
    sorted.length > 0 && sorted.every((r) => r.sim_time_us != null);
  const readingTime = (r) =>
    simulated ? r.sim_time_us / 1000 : Date.parse(r.timestamp);
  const formatTime = (t) =>
    simulated
      ? `${(t / 1000).toFixed(0)} s`
      : new Date(t).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });
  const end = sorted.length ? readingTime(sorted.at(-1)) : 0;
  // Bucket display points only; raw readings remain available through CSV/history.
  const buckets = new Map();
  for (const r of sorted) {
    const time = readingTime(r);
    if (range !== "all" && time < end - Number(range) * 1000) continue;
    const bucket = Math.floor(time / 5000) * 5000;
    const row = buckets.get(bucket) || { time: bucket };
    row[`node${r.node_id}`] = r.temperature;
    buckets.set(bucket, row);
  }
  const data = [...buckets.values()];
  if (!data.length)
    return (
      <div className="empty chart-empty">Waiting for temperature readings</div>
    );
  return (
    <ResponsiveContainer width="100%" height={255}>
      <LineChart
        data={data}
        margin={{ top: 15, right: 10, left: -25, bottom: 0 }}
      >
        <CartesianGrid
          stroke="var(--border)"
          vertical={false}
          strokeDasharray="3 4"
        />
        <XAxis
          dataKey="time"
          minTickGap={35}
          tickLine={false}
          axisLine={false}
          tick={{ fill: "var(--muted)", fontSize: 11 }}
          tickFormatter={formatTime}
        />
        <YAxis
          domain={["auto", "auto"]}
          tickLine={false}
          axisLine={false}
          tick={{ fill: "var(--muted)", fontSize: 11 }}
          tickFormatter={(v) => `${Number(v).toFixed(1)}°`}
        />
        <Tooltip
          contentStyle={{
            background: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 10,
            fontSize: 12,
          }}
          labelFormatter={formatTime}
          formatter={(v, name) => [`${Number(v).toFixed(2)} °C`, name]}
        />
        {nodes
          .filter((n) => selected === "all" || String(n.node_id) === selected)
          .map((n) => (
            <Line
              key={n.node_id}
              type="monotone"
              connectNulls
              dataKey={`node${n.node_id}`}
              name={`Node ${String(n.node_id).padStart(2, "0")}`}
              stroke={colors[(n.node_id - 1) % colors.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              isAnimationActive={false}
            />
          ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
