import { useEffect, useState } from "react";
import {
  Activity,
  ArrowDownToLine,
  ArrowUpRight,
  ChevronRight,
  CircleHelp,
  Clock3,
  Database,
  FileChartColumn,
  Gauge,
  LayoutDashboard,
  Moon,
  Network,
  Radio,
  RefreshCw,
  Server,
  Sun,
  Thermometer,
  Wifi,
  Zap,
} from "lucide-react";
import { get, query } from "./services/api";
import Topology from "./components/Topology";
import TemperatureChart, { colors } from "./components/TemperatureChart";

const number = (v, d = 0) =>
  v == null
    ? "—"
    : Number(v).toLocaleString(undefined, {
        maximumFractionDigits: d,
        minimumFractionDigits: d,
      });
function Metric({ icon: Icon, label, value, unit, detail, accent }) {
  return (
    <article className={`metric ${accent ? "accent" : ""}`}>
      <div className="metric-label">
        <span>{label}</span>
        <Icon size={16} />
      </div>
      <div className="metric-value">
        {value}
        <span>{unit}</span>
      </div>
      <div className="metric-detail">{detail}</div>
    </article>
  );
}
function PanelHeading({ eyebrow, title, children }) {
  return (
    <div className="panel-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h2>{title}</h2>
      </div>
      {children}
    </div>
  );
}

export default function App() {
  const [theme, setTheme] = useState(
    () => localStorage.getItem("wsn-theme") || "dark",
  );
  const [runs, setRuns] = useState([]),
    [runId, setRunId] = useState(""),
    [snapshot, setSnapshot] = useState(null),
    [readings, setReadings] = useState([]);
  const [error, setError] = useState(""),
    [loaded, setLoaded] = useState(false),
    [updated, setUpdated] = useState(null),
    [selected, setSelected] = useState("all"),
    [range, setRange] = useState("all"),
    [tab, setTab] = useState("Overview");
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("wsn-theme", theme);
  }, [theme]);
  useEffect(() => {
    const controller = new AbortController();
    let timer;
    async function poll() {
      try {
        const r = await get("/runs", controller.signal);
        setRuns(r);
        if (!runId && r.length) setRunId(r[0].run_id);
        if (runId) {
          const [s, h] = await Promise.all([
            get(`/dashboard?${query(runId)}`, controller.signal),
            get(`/readings?${query(runId)}&limit=10000`, controller.signal),
          ]);
          setSnapshot(s);
          setReadings(h.items);
          setUpdated(new Date());
        }
        setError("");
        setLoaded(true);
      } catch (e) {
        if (e.name !== "AbortError") {
          setError(e.message);
          setLoaded(true);
        }
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(poll, 2000);
      }
    }
    poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [runId]);
  const changeRun = (id) => {
    setRunId(id);
    setSnapshot(null);
    setReadings([]);
    setSelected("all");
  };
  const s = snapshot?.statistics,
    nodes = snapshot?.nodes || [],
    run = snapshot?.run;
  const exportUrl = `/api/export/readings.csv?${query(runId)}`;
  const visible = nodes.filter(
    (n) => selected === "all" || String(n.node_id) === selected,
  );
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setTab("Overview");
          }}
        >
          <span className="brand-mark">
            <Radio size={22} />
          </span>
          <span>
            fieldwork<span className="brand-dot">.</span>
          </span>
        </a>
        <div className="workspace">
          <div className="workspace-icon">
            <Network size={18} />
          </div>
          <div>
            <strong>WSN Observatory</strong>
            <span>Temperature research lab</span>
          </div>
          <ChevronRight size={14} />
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {[
            [LayoutDashboard, "Overview"],
            [Radio, "Sensor nodes"],
            [Gauge, "Performance"],
            [FileChartColumn, "Experiment report"],
          ].map(([Icon, name]) => (
            <button
              key={name}
              aria-label={name}
              className={tab === name ? "nav-item active" : "nav-item"}
              onClick={() => setTab(name)}
            >
              <Icon size={18} />
              <span>{name}</span>
              {name === "Sensor nodes" && s && <small>{s.total_nodes}</small>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="stack-note">
            <span className="dot" />
            CONTIKI-NG + COOJA
            <div>
              IEEE 802.15.4 · 6LoWPAN
              <br />
              IPv6 · UDP · RPL-Lite
            </div>
          </div>
          <a className="nav-item" href="/docs" target="_blank" rel="noreferrer">
            <CircleHelp size={18} />
            <span>API documentation</span>
            <ArrowUpRight size={14} />
          </a>
          <div className="lab-profile">
            <span>WS</span>
            <div>
              <strong>Wireless systems lab</strong>
              <small>Local research workspace</small>
            </div>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} />
            <strong>{tab}</strong>
          </div>
          <div className="topbar-actions">
            <span className={`connection ${error ? "warning" : ""}`}>
              <i className="dot" />
              {error ? "Connection issue" : "API polling · 2 sec"}
            </span>
            <button
              className="icon-button"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
            >
              {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <div className="avatar">WS</div>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <div className="eyebrow page-eyebrow">
                WIRELESS SENSOR NETWORK / TEMPERATURE
              </div>
              <h1>
                {tab === "Overview"
                  ? "A clearer view of your network."
                  : tab === "Sensor nodes"
                    ? "Every node. Every reading."
                    : tab === "Performance"
                      ? "Performance, measured."
                      : "From experiment to evidence."}
              </h1>
              <p>
                {tab === "Overview"
                  ? "Temperature telemetry and network health, in one place."
                  : tab === "Sensor nodes"
                    ? "Explore individual sensors, routing parents, and received samples."
                    : tab === "Performance"
                      ? "Application delivery, routing traffic, and transparent energy estimates."
                      : "Reproducible Cooja observations with exportable measurement records."}
              </p>
            </div>
            <a
              className={`button secondary ${!run ? "disabled" : ""}`}
              href={run ? exportUrl : undefined}
              aria-disabled={!run}
            >
              <ArrowDownToLine size={15} />
              Export readings
            </a>
          </div>
          <div className="experiment-bar">
            <div className="experiment-name">
              <span className="experiment-symbol">
                <Server size={16} />
              </span>
              <label htmlFor="experiment">Experiment</label>
              <select
                id="experiment"
                value={runId}
                onChange={(e) => changeRun(e.target.value)}
                aria-label="Select experiment"
              >
                {!runs.length && <option value="">No experiments yet</option>}
                {runs.map((r) => (
                  <option key={r.run_id} value={r.run_id}>
                    {r.name}
                  </option>
                ))}
              </select>
              <span className="pill">
                {run?.status === "completed"
                  ? "COMPLETED"
                  : run
                    ? "RUNNING"
                    : "AWAITING DATA"}
              </span>
            </div>
            <div className="experiment-meta">
              <Clock3 size={13} />
              {run ? `${number(s.duration_s, 0)} s observed` : "—"}
              <span className="divider" />
              <RefreshCw size={12} />
              {updated
                ? `Synced ${updated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}`
                : "Connecting"}
            </div>
          </div>
          {error && (
            <div className="error-banner" role="alert">
              {error}.{" "}
              {snapshot
                ? "Displayed measurements are from the last successful update."
                : "Start the backend to connect the observatory."}
            </div>
          )}
          {!snapshot ? (
            <div className="empty initial">
              <Radio size={36} />
              <h2>
                {loaded && !runs.length
                  ? "Your observatory is ready."
                  : "Connecting to your experiment…"}
              </h2>
              <p>
                {loaded && !runs.length
                  ? "Run a Cooja experiment and import its log to see measured telemetry here."
                  : "Fetching sensor readings and network statistics."}
              </p>
              {loaded && !runs.length && (
                <code>bash scripts/run_experiment.sh 5</code>
              )}
            </div>
          ) : (
            <>
              <section className="metrics">
                <Metric
                  icon={Radio}
                  label="Sensor nodes"
                  value={number(s.total_nodes)}
                  detail={`${s.active_nodes} active ${run.status === "completed" ? "at observation end" : "in this experiment"}`}
                />
                <Metric
                  icon={Activity}
                  label="Active sensors"
                  value={number(s.active_nodes)}
                  detail="Received within 15 seconds"
                />
                <Metric
                  icon={Thermometer}
                  label="Average temperature"
                  value={number(s.average_temperature, 1)}
                  unit="°C"
                  detail="Across latest node readings"
                />
                <Metric
                  icon={Thermometer}
                  label="Minimum temperature"
                  value={number(s.min_temperature, 1)}
                  unit="°C"
                  detail="Lowest latest node reading"
                />
                <Metric
                  icon={Thermometer}
                  label="Maximum temperature"
                  value={number(s.max_temperature, 1)}
                  unit="°C"
                  detail="Highest latest node reading"
                />
                <Metric
                  icon={Wifi}
                  label="Packet delivery"
                  value={number(s.pdr, 1)}
                  unit="%"
                  detail={
                    s.pdr == null
                      ? (run.telemetry_complete ? "Waiting for first transmission" : "Requires transmit-side telemetry")
                      : `${number(s.packets_received)} unique readings received`
                  }
                  accent
                />
              </section>
              {(tab === "Overview" || tab === "Sensor nodes") && (
                <div className="main-grid">
                  <section className="panel trend-panel">
                    <PanelHeading
                      eyebrow="SENSOR TELEMETRY"
                      title="Temperature over time"
                    >
                      <div className="segmented">
                        {[
                          ["60", "1 min"],
                          ["300", "5 min"],
                          ["all", "All"],
                        ].map(([v, t]) => (
                          <button
                            className={range === v ? "selected" : ""}
                            onClick={() => setRange(v)}
                            key={v}
                          >
                            {t}
                          </button>
                        ))}
                      </div>
                    </PanelHeading>
                    <div className="chart-subtitle">
                      Degrees Celsius{" "}
                      <span>Simulation seconds · 5 s buckets</span>
                    </div>
                    <TemperatureChart
                      readings={readings}
                      nodes={nodes}
                      selected={selected}
                      range={range}
                    />
                    <div className="chart-legend">
                      {nodes.map((n) => (
                        <button
                          className={
                            selected === String(n.node_id) ? "selected" : ""
                          }
                          key={n.node_id}
                          onClick={() =>
                            setSelected(
                              selected === String(n.node_id)
                                ? "all"
                                : String(n.node_id),
                            )
                          }
                        >
                          <i
                            style={{
                              background:
                                colors[(n.node_id - 1) % colors.length],
                            }}
                          />
                          Node {String(n.node_id).padStart(2, "0")}
                        </button>
                      ))}
                    </div>
                  </section>
                  <section className="panel topology-panel">
                    <PanelHeading
                      eyebrow="ROUTING TOPOLOGY"
                      title="Connected in the field"
                    >
                      <span className="tiny-badge">MULTI-HOP</span>
                    </PanelHeading>
                    <Topology
                      run={run}
                      nodes={nodes}
                      selected={selected}
                      onSelect={setSelected}
                    />
                    <div className="topology-footer">
                      <span>
                        <i className="dot" />
                        {nodes.filter((n) => n.parent_mote_id > 1).length}{" "}
                        relayed nodes
                      </span>
                      <span>
                        {run.metadata.radio_range_m ?? "—"} m radio range
                      </span>
                    </div>
                  </section>
                </div>
              )}
              {(tab === "Overview" || tab === "Sensor nodes") && (
                <section className="panel node-panel">
                  <PanelHeading
                    eyebrow="NODE INVENTORY"
                    title="Sensor activity"
                  >
                    <select
                      aria-label="Filter by sensor"
                      value={selected}
                      onChange={(e) => setSelected(e.target.value)}
                    >
                      <option value="all">All sensors</option>
                      {nodes.map((n) => (
                        <option value={String(n.node_id)} key={n.node_id}>
                          Node {String(n.node_id).padStart(2, "0")}
                        </option>
                      ))}
                    </select>
                  </PanelHeading>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Sensor</th>
                          <th>Status</th>
                          <th>Temperature</th>
                          <th>Received</th>
                          <th>Packet loss</th>
                          <th>RPL parent</th>
                          <th>Last receipt (mapped time)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {visible.map((n) => (
                          <tr key={n.node_id}>
                            <td>
                              <span className="node-icon">
                                <Radio size={15} />
                              </span>
                              <strong>
                                Node {String(n.node_id).padStart(2, "0")}
                              </strong>
                              <span className="node-id">
                                SN-{String(n.node_id).padStart(3, "0")}
                              </span>
                            </td>
                            <td>
                              <span className={`status ${n.status}`}>
                                <i className="dot" />
                                {n.status === "active" ? "Active" : "Offline"}
                              </span>
                            </td>
                            <td>
                              <strong className="temperature">
                                {number(n.temperature, 2)}
                                <small> °C</small>
                              </strong>
                            </td>
                            <td className="mono">
                              {number(n.packets_received)}
                            </td>
                            <td className="mono">
                              {number(n.packets_lost)}{" "}
                              <span className="muted">packets</span>
                            </td>
                            <td>
                              {n.parent_mote_id === 1
                                ? "Sink"
                                : n.parent_mote_id > 1
                                  ? `Node ${String(n.parent_mote_id - 1).padStart(2, "0")}`
                                  : "—"}
                            </td>
                            <td className="muted mono">
                              {n.last_received
                                ? new Date(n.last_received).toLocaleTimeString()
                                : "No reading"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="table-footer">
                    <span>
                      Showing {visible.length} of {nodes.length} sensors
                    </span>
                    <span>
                      {run.status === "completed"
                        ? "Status at the end of the experiment"
                        : "Active = reception within 15 seconds"}
                    </span>
                  </div>
                </section>
              )}
              {(tab === "Overview" || tab === "Performance") && (
                <section className="panel performance-panel">
                  <PanelHeading
                    eyebrow="NETWORK PERFORMANCE"
                    title="The numbers behind the network"
                  >
                    <span
                      className={`status ${s.health === "healthy" ? "active" : "offline"}`}
                    >
                      <i className="dot" />
                      {s.health}
                    </span>
                  </PanelHeading>
                  <div className="performance-grid">
                    {[
                      [
                        Activity,
                        "End-to-end delay",
                        s.average_delay_ms,
                        "ms",
                        "First TX to first RX",
                      ],
                      [
                        ArrowUpRight,
                        "Payload throughput",
                        s.throughput_bps,
                        "bit/s",
                        "Unique payload bits / run time",
                      ],
                      [
                        Network,
                        "Routing control",
                        s.routing_control_packets,
                        "packets",
                        "RPL output events",
                      ],
                      [
                        Zap,
                        "Estimated energy",
                        s.estimated_energy_j,
                        "J",
                        "Energest × assumed currents",
                      ],
                    ].map(([Icon, label, value, unit, detail]) => (
                      <div className="performance-item" key={label}>
                        <Icon size={18} />
                        <div>
                          <span>{label}</span>
                          <strong>
                            {number(value, label === "Routing control" ? 0 : 2)}{" "}
                            <small>{unit}</small>
                          </strong>
                          <p>{detail}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              )}
              {(tab === "Performance" || tab === "Experiment report") && (
                <div className="report-grid">
                  <section className="panel">
                    <PanelHeading
                      eyebrow="DELIVERY ACCOUNTING"
                      title="Every packet accounted for"
                    />
                    <dl className="facts">
                      {[
                        ["Generated samples", s.generated_samples],
                        ["Unique packets sent", s.packets_sent],
                        ["Transmission attempts", s.transmission_attempts],
                        ["Retry attempts", s.retry_attempts],
                        ["Received readings", s.packets_received],
                        ["Lost after transmission", s.packets_lost],
                        ["Samples without a route", s.no_route_samples],
                        ["Duplicate receptions", s.duplicate_receptions],
                        ["Missing sequence numbers", s.sequence_gaps],
                        [
                          "Packet loss ratio",
                          `${number(s.packet_loss_ratio, 2)} %`,
                        ],
                      ].map(([k, v]) => (
                        <div key={k}>
                          <dt>{k}</dt>
                          <dd>{v ?? "—"}</dd>
                        </div>
                      ))}
                    </dl>
                  </section>
                  <section className="panel">
                    <PanelHeading
                      eyebrow="EXPERIMENT NOTES"
                      title="Evidence with context"
                    />
                    <div className="report-copy">
                      <p>
                        <strong>{s.metric_basis}</strong>. Temperatures are
                        generated by the C firmware. Packet delivery and routing
                        observations come from the Cooja network simulation.
                      </p>
                      <p>
                        Energy ({number(s.estimated_energy_j, 2)} J) and time to
                        first sensor battery depletion (
                        {number(s.estimated_network_lifetime_hours, 1)} h) are
                        estimates using a {s.energy_model.voltage_v} V,{" "}
                        {s.energy_model.battery_mah} mAh model. Radio listen and
                        CPU currents are additive.
                      </p>
                      <p>
                        Routing overhead:{" "}
                        <strong>
                          {number(s.routing_overhead_per_data_packet, 2)}
                        </strong>{" "}
                        RPL control output calls per unique application packet.
                        This excludes MAC retries and forwarded control frames.
                      </p>
                      <dl className="facts">
                        <div>
                          <dt>Random seed</dt>
                          <dd>{run.metadata.seed ?? "—"}</dd>
                        </div>
                        <div>
                          <dt>Configured duration</dt>
                          <dd>{run.duration_s} s</dd>
                        </div>
                        <div>
                          <dt>Data source</dt>
                          <dd>{run.source}</dd>
                        </div>
                      </dl>
                      <a className="button secondary" href={exportUrl}>
                        <ArrowDownToLine size={15} />
                        Download raw readings
                      </a>
                    </div>
                  </section>
                </div>
              )}
              {tab === "Sensor nodes" && (
                <section className="panel">
                  <PanelHeading
                    eyebrow="RECEIVED SAMPLES"
                    title="Recent reading history"
                  />
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Timestamp</th>
                          <th>Node</th>
                          <th>Temperature</th>
                          <th>Sequence</th>
                          <th>Boot session</th>
                        </tr>
                      </thead>
                      <tbody>
                        {readings
                          .filter(
                            (r) =>
                              selected === "all" ||
                              String(r.node_id) === selected,
                          )
                          .slice(0, 30)
                          .map((r) => (
                            <tr
                              key={`${r.node_id}-${r.boot_id}-${r.sequence_number}`}
                            >
                              <td className="mono">
                                {new Date(r.timestamp).toLocaleString()}
                              </td>
                              <td>Node {r.node_id}</td>
                              <td>{number(r.temperature, 2)} °C</td>
                              <td>{r.sequence_number}</td>
                              <td className="mono muted">{r.boot_id}</td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              )}
              <footer className="page-footer">
                <span>
                  <Database size={12} />
                  Persisted in SQLite ·{" "}
                  {run.source === "cooja"
                    ? "Cooja simulation"
                    : "Sensor ingestion"}
                </span>
                <span>
                  {run.status === "completed"
                    ? "Historical experiment · availability shown at simulation end"
                    : "Receiving experiment telemetry"}
                  <span className="footer-dot">●</span>
                </span>
              </footer>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
