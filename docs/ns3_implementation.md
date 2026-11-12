# NS-3 implementation

## Toolchain

Pinned release: ns-3.46, official source commit `ea50b72ab79b1ec5912c66d5b384effa829f18bc`. Requires C++23 and CMake 3.20+. Apple Clang 21 is used on this host. Build tools are CMake 4.4.4 and Ninja 1.13.2. See `ns3_environment.md` for host evidence and host build-workspace workaround.

```bash
export NS3_HOME="$PWD/.runtime/ns-3.46"
export NS3_TOOL_BIN="/path/to/local/tool/environment/bin"
bash scripts/build_ns3.sh
```

The build adds a small scratch CMake target referencing this repository's C++ sources. It does not copy NS-3 core sources into the project or modify Contiki. NetAnim's module dependencies cause additional NS-3 libraries to be built; the simulated wireless devices are LR-WPAN, not Wi-Fi or LTE.

## Protocol and network

`TemperatureHeader` serializes the exact existing 18-byte big-endian payload. It has independent exact-byte and round-trip tests, including negative temperature, sequence boundary and invalid identity checks. IPv6, UDP, 6LoWPAN and IEEE 802.15.4 headers are additional transport encapsulation.

The network uses actual LR-WPAN devices, SixLowPanNetDevice adaptation and IPv6 UDP sockets. A fixed range propagation model defines connectivity. Optional losses are independently sampled UDP receive discards for telemetry and application ACKs, after actual wireless delivery. This intentionally differs from PHY loss and Cooja UDGM TX-success settings. MAC behavior remains NS-3's implementation. The initially tested LR-WPAN post-reception RateErrorModel caused an upstream PHY-state null-pointer assertion under loss; its failed run is retained. No NS-3 core patches or calibrated-radio claims are made.

Routing is **static IPv6 breadth-first next-hop routing**, not RPL. The configured neighbor graph determines destination-specific host routes. BFS distances decrease along each route and IPv6 hop limits bound forwarding. Disconnected sensors log no-route samples. No route-discovery control packets are transmitted; static route installation is not wireless routing overhead. There is no dynamic topology/routing repair in this implementation.

UDP application ACKs echo the exact payload. Sensors match source, identity, temperature and sample uptime and accept delayed ACKs for earlier attempts. A bounded timer retries each reading; attempts remain distinct from unique TX. The sink records duplicates/out-of-order packets and ACKs repeats. IPv6 forwarding callbacks record actual forwarding events; hop counts use received hop-limit tags, and packet-path instrumentation follows forwarding callbacks. Instrumentation metadata does not enlarge the telemetry payload.

Temperature generation uses dedicated deterministic random streams and bounded centi-degree random walks. Boot sampling is staggered from 15 to 20 seconds. Outstanding retry work prevents overlapping samples on a sensor; samples are deferred under prolonged ACK waits. Sampling stops early enough to leave the configured retry window before simulation end.

## Energy and time

PHY state transitions accumulate TX and listening microseconds. The existing illustrative current model converts these to energy; CPU is assumed continuously active. This is an estimate, not calibrated board energy or a native LR-WPAN battery model. Remaining energy assumes a 2,000 mAh battery and linear depletion. Energy is included through the final observation time. Actual simulator timestamps determine delay, delivery and throughput; the manifest epoch only maps display timestamps to UTC.

## Operation

Start the same platform with `bash scripts/start_project.sh`. Use the existing dashboard's simulation controls, or:

```bash
bash scripts/run_ns3_experiment.sh 5
bash scripts/run_ns3_experiment.sh 10 --topology ladder
bash scripts/run_ns3_experiment.sh 20 --topology ladder --fast
```

`--fast` disables wall-clock pacing. Each run saves its manifest, flushed events, NetAnim XML and console/terminal-state metadata under `ns3/results/<UUID>/`. To replay a completed recording:

```bash
.venv/bin/python scripts/ns3_bridge.py ns3/results/<UUID>
```

NetAnim XML is generated with the real `AnimationInterface`. If the GUI is installed, open `animation.xml` through NetAnim's file chooser. The GUI is separate from the dashboard. GUI validation has not been performed on this host.

## Contracts and event mapping

No duplicate monitoring API or database was introduced. Existing `/api/runs`, `/api/runs/{id}/events`, `/api/dashboard?run_id=...`, `/api/readings?run_id=...`, `/api/network/statistics?run_id=...` and `/api/export/readings.csv?run_id=...` serve both engines. Added paginated `/api/runs/{id}/events`, explicit `/api/comparison?cooja=...&ns3=...`, and `/api/simulations/ns3/run`, `/{id}/stop`, `/{id}/execution` only for process control.

JSONL retains the existing compact event vocabulary: `started`, `completed`, `initialized`, `online`, `offline`, `sample`, `tx`, `rx`, `forward`, `drop`, `ack`, `ack_timeout`, `retry`, `failed`, `route_established`, `no_route`, `status`, `energy`. Each raw event includes `run_id`, `simulator`, `event_id`, `sim_time_us` and `node_id`; packet events carry boot/sequence/attempt and temperature. `route_changed` is accepted but is not fabricated for static routes. `failed` denotes exhausted application ACK attempts. Drop diagnostics are separate from metric loss, which is calculated from unique TX minus RX identities.

The managed worker streams validated event batches through the existing in-process ingestion function, preserving its transaction/idempotency logic. The CLI replay adapter uses REST with the original bounded-backoff HTTP utility and validates a complete recording before insertion. Managed live execution flushes and tails JSONL; it owns a bounded child process. External already-running processes are not adopted.

Topology paths are reconstructed from actual IPv6 forwarding callbacks; the UI highlights the most recent recorded RX path, with a slowed animation during live execution. It is a monitoring representation, not a physical-time animation. Cooja hop count remains null because the historical contract lacks it.

Build provenance is written after compilation to `wsn-build.json`; launch verifies the executable hash and copies the build's source hashes into each run manifest. It does not confuse a subsequently edited source tree with the already-compiled executable.
