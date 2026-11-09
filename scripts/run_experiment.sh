#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$WSN_ROOT"
NODES="${1:-5}"
OUTPUT="${2:-analysis/results/cooja_${NODES}_$(date +%Y%m%d_%H%M%S)}"
bash scripts/run_simulation.sh "$NODES" "$OUTPUT"
.venv/bin/python analysis/performance_analysis.py "$OUTPUT"
.venv/bin/python scripts/bridge.py "$OUTPUT/COOJA.testlog" --url "${WSN_API_URL:-http://127.0.0.1:8001}"
