# NS-3 engine in the existing WSN platform

This directory adds a real NS-3 3.46 LR-WPAN / 6LoWPAN / IPv6 / UDP implementation to the existing FastAPI/SQLite/React platform. Cooja remains available. Static BFS IPv6 next-hop routing is **not RPL**.

## Run

Start the shared backend/dashboard with `bash scripts/start_project.sh`, then open http://127.0.0.1:8001/ and expand **Simulation engines & comparison**. Select an experiment using the simulator and experiment selectors. Use **Run NS-3 simulation**, **Stop simulation**, progress and output controls in that same dashboard.

```bash
bash scripts/run_ns3_experiment.sh 5
bash scripts/run_ns3_experiment.sh 10 --topology ladder --duration 300 --fast
bash scripts/run_ns3_experiment.sh 20 --topology ladder --interval 2 --seed 42 --fast
```

The shell launcher uses `WSN_PYTHON`, the local runtime pointer, or `.venv/bin/python`. Python utility commands below can use that same interpreter. Example configurations in `config/` can be posted directly to `/api/simulations/ns3/run` with a JSON HTTP client.

```bash
python scripts/ns3_matrix.py
python scripts/validate_ns3_results.py
python scripts/ns3_bridge.py ns3/results/<UUID>
bash scripts/open_netanim.sh ns3/results/<UUID>/animation.xml
```

## Build

Install Apple's command-line C++ tools on macOS if absent (`xcode-select --install`). The tested compiler is Apple Clang 21 with C++23 support. On a fresh clone, `bash scripts/setup_ns3.sh` obtains the pinned official NS-3 release and local CMake/Ninja tools. Set `NS3_HOME` to reuse an existing inspected **3.46** source tree. The setup refuses an incompatible existing directory instead of overwriting it. Do not point it at a different release without adapting and retesting the APIs.

`bash scripts/build_ns3.sh` adds scratch targets to that external NS-3 tree and references project sources. Set `NS3_TOOL_BIN` for an existing CMake/Ninja environment and `NS3_RUNTIME` for build outputs. No NS-3 core files are duplicated in this directory. Successful builds run the real header test and write build provenance and `.runtime/ns3-runtime-path` for backend discovery.

See [environment](../docs/ns3_environment.md) for this machine's installed runtime and build commands, [implementation](../docs/ns3_implementation.md) for protocol/routing/reliability, [actual results](../docs/ns3_experimental_results.md), and [comparison](../docs/cooja_vs_ns3_comparison.md).

## Layout and limitations

- `scratch/`: NS-3 executable entry point.
- `src/`: header, sensor, sink, routing, PHY-state telemetry and simulation configuration/setup.
- `tests/`: compiled 18-byte wire-format checks.
- `scripts/`: build provenance support.
- `config/`: 5/10/20-node presets.
- `results/<UUID>/`: independent manifest, actual JSONL, NetAnim XML, console and execution state; analysis adds readings/nodes/metrics CSV, summary and plots.

The payload is deliberately fixed at 18 bytes. Optional receive discards operate at UDP, including ACKs, after wireless delivery; they are not PHY errors. Routing is static, topology fixed, and energy estimated from observed PHY-state durations plus assumed CPU current. NetAnim GUI is optional and was unavailable on the test host. The React topology uses backend records and does not require NetAnim. It displays a slowed path animation of the latest recorded packet, not a claim of packet travel at wall-clock speed.
