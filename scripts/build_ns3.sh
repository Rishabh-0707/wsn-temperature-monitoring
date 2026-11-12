#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NS3_HOME="${NS3_HOME:-$ROOT/.runtime/ns-3.46}"
NS3_RUNTIME="${NS3_RUNTIME:-$ROOT/.runtime/ns3-runtime}"
export PATH="${NS3_TOOL_BIN:-$ROOT/.venv/bin}:$PATH"
[[ -f "$NS3_HOME/ns3" ]] || { echo 'Set NS3_HOME to the inspected ns-3.46 source checkout.' >&2; exit 1; }
command -v cmake >/dev/null || { echo 'Install CMake and Ninja in a local tool environment; set NS3_TOOL_BIN to its bin directory.' >&2; exit 1; }
mkdir -p "$NS3_HOME/scratch/wsn-platform"
python3 - "$ROOT" "$NS3_HOME" <<'PY'
import sys
from pathlib import Path
root, home = map(Path,sys.argv[1:])
source=root/'ns3'
(home/'scratch/wsn-platform/CMakeLists.txt').write_text(f'''build_exec(EXECNAME wsn-header-test
 SOURCE_FILES "{source}/tests/header-test.cc" "{source}/src/temperature-header.cc"
 HEADER_FILES "{source}/src/temperature-header.h"
 LIBRARIES_TO_LINK ${{libcore}} ${{libnetwork}}
 EXECUTABLE_DIRECTORY_PATH "${{CMAKE_OUTPUT_DIRECTORY}}/scratch/wsn-platform/")
get_scratch_prefix(wsn_prefix)
target_include_directories(${{wsn_prefix}}wsn-header-test PRIVATE "{source}/src")
build_exec(EXECNAME wsn-temperature
 SOURCE_FILES "{source}/scratch/wsn-temperature.cc" "{source}/src/temperature-header.cc"
 "{source}/src/telemetry.cc"
 "{source}/src/sensor-application.cc"
 "{source}/src/sink-application.cc"
 "{source}/src/network-forwarder.cc"
 "{source}/src/simulation.cc"

 LIBRARIES_TO_LINK ${{libcore}} ${{libnetwork}} ${{libinternet}} ${{liblr-wpan}} ${{libsixlowpan}} ${{libmobility}} ${{libpropagation}} ${{libspectrum}} ${{libnetanim}}
 EXECUTABLE_DIRECTORY_PATH "${{CMAKE_OUTPUT_DIRECTORY}}/scratch/wsn-platform/")
target_include_directories(${{wsn_prefix}}wsn-temperature PRIVATE "{source}/src")
''')
PY
cd "$NS3_HOME"
python3 ns3 configure --out="$NS3_RUNTIME" --enable-modules=core,network,lr-wpan,sixlowpan,internet,mobility,propagation,spectrum,energy,flow-monitor,netanim --disable-examples --disable-tests
cmake --build cmake-cache --target scratch_wsn-platform_wsn-header-test scratch_wsn-platform_wsn-temperature -j 4
"$NS3_RUNTIME/scratch/wsn-platform/ns3.46-wsn-header-test-default"
python3 "$ROOT/ns3/scripts/build_manifest.py" "$ROOT" "$NS3_RUNTIME"
printf '%s\n' "$NS3_RUNTIME" > "$ROOT/.runtime/ns3-runtime-path"
