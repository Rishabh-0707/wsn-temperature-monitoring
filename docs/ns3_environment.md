# NS-3 environment report — 10 November 2026

Inspected macOS Darwin arm64, Apple Clang 21.0.0, Python 3.13 and Node 26. No NS-3 or NetAnim installation was found in the usual home, Documents, Downloads, Applications, /opt, /usr/local, Spotlight or Docker locations. The user confirmed no existing installation. Unrelated Docker services were left untouched.

Installed one official source release: **ns-3.46**, commit `ea50b72ab79b1ec5912c66d5b384effa829f18bc`, under ignored `.runtime/ns-3.46`. [Official source](https://github.com/nsnam/ns-3-dev-git) and [release installation guide](https://www.nsnam.org/docs/release/3.46/installation/ns-3-installation.pdf). Its actual CMake files require C++23 and CMake >=3.20; inspected local examples/headers supplied the API references. CMake 4.4.4 and Ninja 1.13.2 were used.

The following modules were available and enabled in configuration: core, network, LR-WPAN, sixlowpan, internet, mobility, spectrum, propagation, energy, flow-monitor and netanim (including their dependencies). The simulation links real LR-WPAN/SixLoWPAN/IPv6 and `AnimationInterface`. The Energy Framework library was built; FlowMonitor is available but is not linked by this executable. Module availability does not imply these frameworks calculate this application's metrics: the adapter uses unique application telemetry and a documented PHY-state current estimate. No compatible built-in LR-WPAN battery device model is claimed.

## Host runtime locations

The host exhibited intermittent long regular-file reads under Documents, including the old virtual environment and generated C++ precompiled headers. A fresh environment with the **unchanged backend lockfile** passed tests. The same pinned NS-3 checkout was exported, without a second download, to `/private/tmp/wsn-ns3-build-source` for compilation.

Persistent executable/libraries: `/Users/rishabhsinghparmar/Library/Application Support/wsn/ns3-runtime`.
Persistent Python runtime: `/Users/rishabhsinghparmar/Library/Application Support/wsn/python`.
The ignored `.runtime/ns3-runtime-path` and `.runtime/python-path` select those runtimes. `WSN_PYTHON` and `NS3_RUNTIME` override them. The original `.venv` was retained. These are host-local paths, not requirements for other clones.

Executed build:

```bash
NS3_HOME=/private/tmp/wsn-ns3-build-source \
NS3_RUNTIME="$HOME/Library/Application Support/wsn/ns3-runtime" \
NS3_TOOL_BIN=/private/tmp/wsn-ns3-tool-env/bin \
bash scripts/build_ns3.sh
```

The temporary build workspace may be recreated from the retained pinned checkout if removed. The installed executable and shared libraries do not depend on that temporary source tree. For other machines use `scripts/setup_ns3.sh`; for this host normal simulation launch requires no rebuild.

## Validation and limitations

Both project C++ targets compiled and the executable header test passed. Actual 5/10/20-node networks, retries, multi-hop paths and NetAnim XML ran successfully. NetAnim **GUI was not installed**, so XML was parsed and checked for nodes/wireless packet records, but not played in the GUI. `scripts/open_netanim.sh` supplies an explicit command once the GUI is available. No system security settings or existing Contiki installation were changed.

On 12 November the earlier Documents read stalls were confirmed on macOS files marked `compressed,dataless` (cloud-offloaded), including generated compiler dependency files. Rebuilding the preserved generated Cooja cache allowed the unchanged firmware and fresh live simulation to pass. Keep active build/runtime artifacts locally available; the persistent NS-3/Python runtimes already reside outside Documents. No cloud files or original experiments were deleted.
