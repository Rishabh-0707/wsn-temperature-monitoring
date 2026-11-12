# Project status

## Plan and validation gates

1. Inspect host, workspace, and existing Contiki-NG/Cooja. **Complete**: empty workspace; macOS arm64, Python 3.13, Node 26, Java 23, make/clang; existing Contiki-NG at `~/contiki-ng` (commit `735e87c3e`) and Cooja (`be0f8d8`). Existing installation has changes and will not be modified.
2. Design architecture, wire protocol, metric definitions, and reproducibility. **Complete**.
3. Implement and compile temperature sensor. **Complete**: native Cooja compilation succeeded.
4. Implement and compile sink. **Complete**: native Cooja compilation succeeded.
5. Configure existing RPL-Lite and multi-hop topology. **Complete**: observed parent links and receptions from nodes outside direct radio range.
6. Generate, validate, and execute 5/10-sensor Cooja experiments. **Complete**: both 300-second baselines report TEST OK; separate structural/evidence validators pass.
7. Implement FastAPI, SQLite persistence, and metric tests. **Complete**: eight automated tests pass, including partial-line streaming and stalled-log handling.
8. Connect simulator serial logs to backend with idempotent ingestion. **Complete**: 1,900 and 3,622 events imported through HTTP.
9. Implement React/Vite/Tailwind/Recharts dashboard and verify build/UI. **Complete**: production build passed in the workspace and from a clean temporary dependency installation with matching source hashes. Desktop/mobile interactions, themes, node/time filters, experiment selection, history, CSV download and live updates were exercised in the browser.
10. Export observed results, CSV, and performance graphs. **Complete**: baseline summaries, per-node/event/reading CSVs, SVG/PNG performance plots and comparison chart generated.
11. Run integration tests and resolve failures. **Complete**: baseline chain, Java 23 regression, real-time log-to-API streaming, persistence and frontend integration verified. Extra lossy stress test retained with its observed failed connectivity result.
12. Complete report, diagrams, reproducibility instructions, and evidence. **Complete**: full 18-section academic report, architecture/topology/flow diagrams, plots, CSVs, manifests, raw logs and setup instructions delivered. Local Markdown links validated.

## Environment findings

- Docker is available but unnecessary for the verified native workflow. Existing unrelated Docker services were left unchanged.
- Existing Cooja jar requires Java 25; default runtime is Java 23. Initial baselines used project-local Temurin 25.0.5+8 with an officially verified archive hash, but macOS intermittently killed that runtime. The resolved launcher compiles unchanged existing Cooja sources into a separate Java 23 jar under `.runtime/cooja-java23`; the original installation is untouched. A ten-sensor regression exactly reproduced six baseline metrics, and the live test passed on Java 23. No system security settings changed.
- macOS Make 3.81 is too old. Built GNU Make 4.4.1 inside `.runtime/toolchain` and successfully compiled both applications.
- Cooja clears most compile environment variables. A generated project-local `.runtime/contiki.mk` supplies the installation path. Single-job compilation avoids sandbox FIFO restrictions.
- Default port 8000 belongs to an existing Docker application. This project uses loopback port 8001.
- No project code existed to preserve in this workspace.
- Actual source examples and headers under the existing Contiki-NG installation are the API reference.

## Measurement contract

- Real Cooja execution is the primary source. Never label synthetic/test data as simulator results.
- Unique transmitted application packets form the PDR denominator; retries, generated samples, and no-route skips are separate counters.
- Cooja's global simulation timestamps determine delay and throughput. UTC is assigned by an explicit run epoch in the bridge; no claim of synchronized hardware clocks.
- Energest times are measurements; electrical energy and lifetime are estimates with explicit current/battery assumptions.
- RPL control transmissions are counted from the existing stack's INFO logs, not invented network counters.

## Test evidence

- Baseline 5: 279/279 packets, 100% PDR, 47.4539 ms average delay, 133.92 payload bit/s, 6 samples skipped without a route. Raw evidence: `analysis/results/baseline_5/COOJA.testlog`.
- Baseline 10: 530/530 packets, 100% PDR, 77.8089 ms average delay, 254.40 payload bit/s, 40 samples skipped without a route. Raw evidence: `analysis/results/baseline_10/COOJA.testlog`.
- Both report all configured sensors received and `multihop: true`; standalone evidence validators also pass.
- Extra stress experiment with UDGM TX success 0.6: 12/15 packets, 80% PDR, 8 application retry attempts, 4 ACK failures, 270 no-route samples. Four of five sensors delivered at least one reading; all are offline at the end. Cooja correctly reports TEST FAILED for its all-sensors criterion. This is an observed network failure, not a successful baseline or fabricated result.
- `python -m pytest -q`: 8 passed; one upstream Starlette/AnyIO deprecation warning.
- C wire-format test compiled with `-std=c99 -Wall -Wextra -Werror` and exited successfully, covering exact 18-byte serialization, signed temperature and integer boundary values.
- `npm run build`: passed, 1,942 modules transformed. A non-fatal warning remains for the approximately 610 kB minified chart/application bundle (182 kB gzip). Intermittent host file-read delays were bypassed with a clean temporary install; the workspace build subsequently passed too.
- Java 23 ten-node regression: TX/RX totals, mean delay, throughput, RPL control count and estimated energy exactly matched `baseline_10`; evidence is `analysis/results/java23_10/regression.json`.
- Real-time streaming: `analysis/results/live_verified_5` completed 60 simulated seconds in 60.081 wall seconds, delivered 39/39 packets, and passed all-sensors/multi-hop checks. `midrun_api.json` preserves the running state; the browser was also observed updating before completion.
- Browser QA: 390 px mobile layout had no page-wide overflow; desktop charts, routing topology and sensor table displayed real API data. Exported CSV contained the expected 39 live-test readings. Screenshots are under `docs/figures/`.
- Final production handoff: `bash scripts/start_project.sh` serves the dashboard and API at `http://127.0.0.1:8001/`. After restart, health, HTML, generated JS/CSS and all monitoring GET endpoints returned 200; the persisted ten-sensor run still reported 530 receptions. Evidence is `analysis/results/production_http_check.json`. The production page showed no browser console errors. The Vite development server was stopped.
- All shell scripts passed individual `bash -n` checks; backend, analysis and simulation/bridge Python modules passed `compileall`. Report figures were visually inspected and local Markdown links resolved.

## Remaining scope and limitations

No required implementation phase remains. Physical sensor integration is an explicit adapter hook and has not been tested on a board. Temperatures are generated in simulated firmware; network behavior is executed by Cooja. Energy/lifetime use documented illustrative electrical assumptions. Results are single-seed observations, and the lossy stress experiment intentionally remains a failed network acceptance result. The local service has no authentication and binds to loopback by default; no cloud deployment was requested.

## NS-3 integration — implemented and verified (12 November 2026)

The original Cooja deliverable above remains intact. Added NS-3 3.46 LR-WPAN / SixLoWPAN / IPv6 / UDP with static BFS next-hop routes, exact 18-byte header, deterministic sensors, sink deduplication, application ACK/retry timers, actual forwarding/hop traces, JSONL and NetAnim XML. Both engines share the existing FastAPI/SQLite tables, metric service, React dashboard and CSV exports. No schema rewrite or Cooja parser change was needed.

The same dashboard now provides engine selection, identifiable experiment history, NS-3 configuration/run/stop/progress/output, recorded packet topology, energy estimates and explicit Cooja/NS-3 comparison tables/graphs. The API uses bounded typed parameters and fixed executable arguments without a shell; concurrent jobs are rejected and cancellation has bounded termination.

Verification: compiled C++ network and exact-byte header tests; all eight real NS-3 matrix processes completed; raw JSONL/metric/CSV/NetAnim checks passed; 15 Python tests passed (all original 8 retained). Additional no-route, full-discard, live cancellation, concurrency and idempotent REST replay checks passed. The twenty-sensor run received 1,127 unique packets with 5.506 average hops. The 30% UDP discard run received 548/563, with 444 retries and 80 ACK failures separately accounted. Original Cooja protocol and 5/10 baseline validators passed. All original 4 runs, 6,184 events and 887 readings matched the pre-integration SQLite backup exactly.

The production frontend build passed; browser checks exercised Cooja/NS-3 history, comparison charts, live readings, launch/stop and themes. See the NS-3 experimental report and `ns3/results/verification/` for final evidence, including responsive and restart checks. Original Cooja experimental reports and baseline metrics were not rewritten.

Runtime: `bash scripts/start_project.sh` on port 8001; `bash scripts/run_ns3_experiment.sh 5` or `10 --topology ladder`. Host runtimes are recorded in ignored `.runtime/*-path` files; details and fresh installation instructions are in `docs/ns3_environment.md` and `ns3/README.md`.

Known limits: fixed 18-byte payload, fixed topology, static routing (not RPL), UDP discard injection (not PHY errors), estimated electrical energy, single-process local job manager, single-run descriptive comparisons. NetAnim XML generation/parsing passed; optional NetAnim GUI was not installed and GUI playback is not claimed. Failed development experiments remain labeled separately from accepted runs. One upstream Python deprecation and a nonfatal frontend bundle-size warning remain.

Final continuation: a fresh unchanged Cooja simulation passed TEST OK and was ingested into the same backend (39/39 packets, 60 s). Cloud-offloaded generated compiler caches caused the first extra attempt to time out; the caches were preserved and rebuilt. Final tests also cover atomic execution-artifact handling and the post-process `ingesting` status. Verification records retain the interrupted attempt separately.
