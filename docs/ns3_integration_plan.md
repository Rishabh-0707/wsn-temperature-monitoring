# NS-3 integration plan

Inspection date: 10 November 2026. Starting revision: `6c18736`.

## Existing contracts and compatibility

`backend/app/main.py` creates FastAPI and mounts the built React app. SQLite uses runs, events and readings tables with WAL. Runs retain extensible JSON metadata; events are unique by `(run_id,event_id)` and readings by `(run_id,node_id,boot_id,sequence_number)`. `/api/runs` registers experiments; `/api/runs/{id}/events` validates batches of up to 500 events and converts RX events into readings transactionally. `/complete` finalizes an observation. The direct `/readings` route deliberately refuses measured experiments. Dashboard, history, node metrics and CSV already select by run ID.

`services.summarize` deduplicates application TX/RX, uses first transmission/receipt timestamps and separates no-route samples, retries and ACK failures. Preserve these calculations. Its Cooja-only simulation-clock availability condition needs extension. The Event model has a closed vocabulary; new NS-3 diagnostic events need explicit typed fields. The source enum also needs `ns3`.

The React App polls every two seconds and cancels stale requests when switching experiments. The topology consumes metadata positions and parent mote IDs (logical ID + 1). It currently hardcodes RPL labels and fixed vertical scaling. The Cooja bridge hashes line identities and retries HTTP transport/server errors; reuse its transport behavior without changing its parsing contract. The analysis module already reuses backend metrics.

## Implementation sequence and gates

1. Capture existing Git evidence inventory and SQLite backup; execute original tests.
2. Inspect/install one local NS-3 toolchain, read its examples/headers, compile an isolated external CMake target.
3. Implement and test an exact 18-byte ns3::Header, deterministic sensors, sink validation and bounded ACK retries.
4. Use real LR-WPAN, SixLoWPAN and IPv6/UDP. Prefer explicitly configured static next-hop IPv6 routes derived from a breadth-first tree; this is static routing, not RPL. Track actual forwarding traces, hop limits, packet identities and observed paths. Record routing setup separately from transmitted routing traffic.
5. Produce flushed JSON Lines with run/engine provenance and simulator microseconds; import through existing endpoints. Keep NetAnim as a separate artifact.
6. Extend metadata and diagnostics backward-compatibly; do not rewrite existing metadata on reads or add defaults that break old run replay equality. Add controlled launch/cancel/status APIs with bounded validated configurations, fixed executable, argument arrays, no shell, concurrency limit and wall timeout. Use a test database/server before changing the running process.
7. Extend existing UI with engine selection, launch controls, status, generic topology/packet visualization and explicit two-run comparison. Preserve existing views and themes.
8. Run star 5, ladder 10 and scalable 20 plus interval/loss/range/seed variants. Export actual results under ns3/results; never replace Cooja outputs.
9. Run existing and new tests, Cooja evidence checks, persistence/replay/isolation checks, production build and browser QA. Record limitations and executed evidence.

## File inventory

Modify: backend/app/models.py, routes.py, services.py and minimal main.py lifecycle wiring; frontend/src/App.jsx, components/Topology.jsx, services/api.js and scoped styles; README.md and PROJECT_STATUS.md.

Add: ns3 C++ application/header/routing/config modules and external CMake build; scripts/build_ns3.sh, run_ns3_experiment.sh, ns3_bridge.py and experiment automation; backend simulation process manager; frontend NS-3 configuration/comparison components; NS-3 tests; requested documentation and environment report.

Preserve unchanged: contiki/**, scripts/bridge.py and existing Cooja runners, analysis/results/**, docs/experimental_results.md, original baseline metric values and existing SQLite rows. Original tests remain regression checks, not rewritten expectations.

## Risks and decisions

No upstream RPL equivalence is assumed. Static routes differ from RPL convergence and repair. Range-limited propagation differs from Cooja UDGM; record both. Native LR-WPAN energy compatibility must be checked; otherwise use actual PHY-state durations with an explicitly illustrative current model. Do not infer Cooja packet hop counts from RPL rank. Maintain null for unavailable metrics. Preserve 18-byte telemetry: configurable packet size must reject unsupported values rather than silently change the protocol. Fast experiments finish between polls; paced execution must be selectable. Failures/cancellation must end running state. No cloud deployment or arbitrary command execution is introduced.

## Final progress

Inspected actual code and running services before edits, captured the original database backup and Git evidence, installed the pinned official NS-3 release, and implemented the integration incrementally. C++ compilation, real matrix runs, backend persistence/isolation/replay, original regressions and shared-dashboard checks are recorded in `ns3_experimental_results.md`. The file inventory remains additive/minimal; the existing Cooja bridge, firmware, baseline evidence and original report are unchanged. `scripts/start_project.sh` additionally supports an explicit/local Python runtime pointer. The existing frontend API helper required no changes.
