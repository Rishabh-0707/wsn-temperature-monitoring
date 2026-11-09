# Implementation and operation

## Host inspection and selected toolchain

The initial workspace was empty. `~/contiki-ng` contained an existing development checkout and a built Cooja jar. Its application examples and actual headers were read before implementing calls to `simple_udp_register`, `simple_udp_sendto`, `NETSTACK_ROUTING.root_start`, `get_root_ipaddr`, RPL neighbor access and Energest. No custom routing implementation was introduced.

The macOS default `make` is 3.81, but this Contiki revision requires 4.0+. GNU Make 4.4.1 was built in `.runtime/toolchain`; `scripts/env.sh` places it first on PATH. The existing Cooja jar is Java class version 69 (Java 25), while the initial system default was Java 23. A project-local Java 25 runtime ran the original baselines but experienced intermittent macOS startup termination. The final local route uses an isolated jar compiled from unchanged Cooja source with the installed Java 23 JDK. The ten-sensor regression reproduced the baseline metrics exactly.

To recreate that isolated compatibility jar for the recorded Cooja source revision:

```bash
python3 scripts/prepare_cooja_java23.py
```

The helper reuses existing Cooja dependencies/resources and writes only `.runtime/cooja-java23`. On macOS it locates the installed Java 23 JDK; elsewhere pass `--java-home /path/to/jdk23`. `scripts/env.sh` selects this jar/JDK automatically when no explicit `JAVA_HOME` is set. This is a tested local compatibility build, not a claim that every future upstream Cooja release supports Java 23.

For another machine, install GNU Make 4+, a C compiler, a Java runtime supported by the pinned Cooja revision, Python 3.13 and a Vite-compatible Node release. Then set `CONTIKI` and `JAVA_HOME` and run `scripts/setup.sh`. Prefer the documented Contiki-NG installation procedure over replacing an existing checkout. A typical fresh pinned checkout is:

```bash
git clone https://github.com/contiki-ng/contiki-ng.git ~/contiki-ng
cd ~/contiki-ng
git checkout 735e87c3e5060e9c427b214e55c372967f595c04
git submodule update --init tools/cooja
git -C tools/cooja checkout be0f8d813271898c6b1cb7cfaec1f692e319a2ec
cd tools/cooja
./gradlew jar
```

The Java toolchain and downloads required by that checkout's Gradle build must be available. These fresh-install commands are reproducibility instructions; the original implementation reused the already-installed tree.

## Firmware build and controls

```bash
bash -c 'source scripts/env.sh; make -C contiki/temperature-sensor TARGET=cooja -j4'
bash -c 'source scripts/env.sh; make -C contiki/sink-node TARGET=cooja -j4'
```

Cooja also compiles each mote type when loading its `.csc` configuration. The Makefiles read `.runtime/contiki.mk` because Cooja deliberately strips HOME/CONTIKI from its build environment. `run_simulation.sh` writes this local file from the selected installation. The shared source tree remains unchanged.

Defaults: five-second sampling, 20–35 °C simulated range, three total application attempts, one-second ACK timeout, ports 8765/5678, CSMA MAC and RPL-Lite routing. Cooja uses PAN `0xabcd` and channel 26 from the existing platform defaults. Boot sampling starts at 15–20 seconds to reduce simultaneous contention; periodic phases remain staggered.

To change an interval or bounds, edit `common/project-conf.h`, clean both application builds, and rerun. Alternatively pass Contiki's `DEFINES=SAMPLE_INTERVAL_SECONDS=10,TEMP_MIN_CENTI=1800,TEMP_MAX_CENTI=3200` to the make commands in a simulation variant. Use intervals of at least three seconds with the default three-attempt retry policy. Preserve the actual `.csc` and define values alongside results.

The simulated temperature model is a bounded centi-degree random walk, with ±0.30 °C change per sample and seed supplied by Cooja. It is a test signal, not a calibrated environmental process. Defining `WSN_HARDWARE_SENSOR` replaces the inline model with `int16_t wsn_read_temperature_centi(void)`; provide a board-specific implementation and include that source in `PROJECT_SOURCEFILES`. Choose a board-supported Contiki target, map IDs, and verify its driver electrically before claiming hardware support.

## Wire protocol

| Byte offsets | Field | Encoding |
|---|---|---|
| 0 | Version | u8, value 1 |
| 1–2 | Logical sensor ID | u16 big-endian; 1–32 |
| 3–6 | Sequence number | u32 big-endian; starts at 1 |
| 7–8 | Temperature | signed i16 centi-degrees, big-endian |
| 9–12 | Sample uptime | u32 milliseconds |
| 13–16 | Boot identifier | u32 pseudo-random nonce |
| 17 | Attempt | u8; 1, 2, or 3 |

The sink validates length, version, node/temperature/sequence/attempt bounds before reading data. It tracks the highest sequence for each boot and logs whether a packet may be duplicated or reordered. It ACKs repeats too, since the previous ACK may have been lost. The database uses the full key to distinguish duplicates from late arrivals. ACK matching verifies the sink address and all identity/data bytes, while accepting a delayed ACK for an earlier attempt of the same sample.

A boot nonce is probabilistic; use a persistent boot counter or high-entropy hardware identifier for deployments that need strict identity across resets. Cooja mote IDs 2–11 map to logical sensors 1–10. Parent IDs are decoded from the Cooja link-local address pattern; this topology adapter is Cooja-specific and must be replaced with an address registry on real hardware.

## Routing and energy

The root starts Contiki's RPL-Lite DAG. Sensors send only after the stack reports reachability and provides a root address. Adjacent relays in the ladder topology are within 50 m; farther sensors cannot reach the sink directly. Parent/rank logs and successful receptions from these outer nodes provide multi-hop evidence. Rank is a routing cost and is not treated as an exact hop count.

RPL INFO logging counts output calls for DIS/DIO/DAO/DAO-ACK. This includes retransmitted control messages when output is called again but excludes forwarded control frames and lower-layer MAC retransmissions. Energy logs call `energest_flush` and record cumulative CPU/LPM/deep-LPM/TX/listen ticks and their frequency. The latest sample per node/boot gives observation duration; energy stops at that sample and may omit up to one sampling interval at simulation end. The sink is included in network energy but excluded from first-sensor-depletion lifetime.

Compact packets, event timers and bounded retries avoid unnecessary CPU work and unlimited radio attempts. The default CSMA radio remains mostly listening: no low-power radio duty-cycle claim is made. TSCH/Orchestra and calibrated hardware models are future work.

## Serial forwarding and clocks

The Cooja ScriptRunner captures every mote's serial messages and attaches the simulator's global microsecond timestamp. The bridge parses JSON telemetry and recognized RPL control messages, then posts batches to the backend. HTTP timeouts and server errors use bounded backoff; validation errors fail loudly. Event IDs hash the original line number and text, so replaying the same unmodified file is idempotent. Do not strip/reorder lines before replaying an existing experiment.

`run_live.sh` adds a speed limit of one simulated second per wall second and runs the bridge with `--follow`. The generated test script reapplies the speed limit at startup because headless Cooja resets the XML setting. Partial log lines are buffered; a stalled producer raises an idle timeout rather than hanging indefinitely. `run_experiment.sh` performs a fast batch experiment, analyzes it and imports it. No MQTT broker or serial-port dependency is needed for this Cooja route.

Packet delay uses global first TX and first RX times, not separately initialized mote clocks. ISO receipt timestamps are an explicit run epoch plus simulation time. Uptime remains in the wire/log for sensor provenance. Physical serial capture needs a host adapter and time synchronization; receiving only the sink's output cannot produce measured PDR or synchronized end-to-end delay. The direct-reading API supports that case with unavailable transmit-derived metrics.

## Data integrity and metric behavior

Runs isolate experiments. Events are unique by `(run_id,event_id)`; readings by `(run_id,node_id,boot_id,sequence_number)`. Whole batches use a transaction. Conflicting event identity returns 409, invalid values/bounds return 422, and missing experiments return 404. Earlier out-of-order receptions replace a later receipt timestamp for the same sample. Sequence gaps are calculated separately per boot as maximum received sequence minus unique received count, including leading gaps; unseen tail losses require TX evidence.

SQLite uses WAL and indexes on run/time. Timestamps must have an explicit offset and are normalized to UTC. History pagination is bounded. The dashboard cancels stale requests when switching runs and retains prior data with an error banner on connection loss. Its chart is a visualization of recent raw records, not a new statistical estimator.

## Failure diagnosis

- Java class-version error: use `prepare_cooja_java23.py` for the recorded source revision, or select Java 25 for the original installed jar.
- Java spawn-helper failure: the runner passes `-Djdk.lang.Process.launchMechanism=FORK`. The recorded Java 25 download had intermittent macOS signature/termination problems; the isolated Java 23 build avoids that download. Do not disable Gatekeeper or system protections.
- Contiki include path missing: set `CONTIKI`, then rerun the wrapper to generate `.runtime/contiki.mk`.
- Old GNU Make: source `scripts/env.sh` or install Make 4+; on macOS a package-manager installation may be called `gmake`.
- No packets: inspect `status`/`no_route` events, topology distances, simulation duration and radio success settings.
- Live API bind failure: use a free `WSN_PORT` and match the bridge/Vite `WSN_API_URL`.
- Cooja TEST FAILED under the lossy configuration: inspect `received_nodes` and `multihop` in `WSN_META`; completion and successful connectivity are different conditions.

An installed Docker image was inspected during host diagnosis, but the container-mount trial did not complete and is not a supported launch path in this deliverable. Native execution is the verified path; Docker is not required. `scripts/bootstrap_make.sh` can recreate the tested project-local GNU Make 4.4.1 installation from a checksum-verified archive.
