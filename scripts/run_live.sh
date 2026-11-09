#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$WSN_ROOT"
NODES="${1:-5}"
DURATION="${2:-300}"
OUTPUT="${3:-analysis/results/live_${NODES}_$(date +%Y%m%d_%H%M%S)}"
.venv/bin/python scripts/generate_simulations.py --nodes "$NODES" --duration "$DURATION" --speed 1 --suffix live
WSN_SIMULATION="contiki/simulations/wsn_${NODES}_nodes_live.csc" bash scripts/run_simulation.sh "$NODES" "$OUTPUT" &
SIM_PID=$!
trap 'kill "$SIM_PID" 2>/dev/null || true' EXIT INT TERM
for ((i=0; i<120; i++)); do
  [[ -f "$OUTPUT/COOJA.testlog" ]] && break
  kill -0 "$SIM_PID" 2>/dev/null || { wait "$SIM_PID"; exit 1; }
  sleep 1
done
[[ -f "$OUTPUT/COOJA.testlog" ]] || { echo 'Cooja log did not appear within 120 seconds.'; exit 1; }
.venv/bin/python scripts/bridge.py "$OUTPUT/COOJA.testlog" --follow --url "${WSN_API_URL:-http://127.0.0.1:8001}"
wait "$SIM_PID"
trap - EXIT INT TERM
.venv/bin/python analysis/performance_analysis.py "$OUTPUT"
