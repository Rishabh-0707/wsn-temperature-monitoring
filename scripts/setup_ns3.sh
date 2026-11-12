#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NS3_HOME="${NS3_HOME:-$ROOT/.runtime/ns-3.46}"
if [[ ! -f "$NS3_HOME/ns3" ]]; then
  if [[ -e "$NS3_HOME" ]]; then echo "Existing directory is not an NS-3 checkout: $NS3_HOME" >&2; exit 1; fi
  git clone --depth 1 --branch ns-3.46 https://github.com/nsnam/ns-3-dev-git.git "$NS3_HOME"
fi
if [[ "$(cat "$NS3_HOME/VERSION")" != "3.46" ]]; then echo 'This adapter is tested against NS-3 3.46; select that checkout.' >&2;exit 1;fi
TOOLS="$ROOT/.runtime/ns3-tools"
[[ -x "$TOOLS/bin/python" ]] || python3 -m venv "$TOOLS"
"$TOOLS/bin/python" -m pip install cmake==4.4.4 ninja==1.13.2
NS3_HOME="$NS3_HOME" NS3_TOOL_BIN="$TOOLS/bin" bash "$ROOT/scripts/build_ns3.sh"
