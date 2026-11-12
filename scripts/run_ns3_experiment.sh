#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ -z "${WSN_PYTHON:-}" && -f .runtime/python-path ]]; then WSN_PYTHON="$(cat .runtime/python-path)"; fi
exec "${WSN_PYTHON:-$ROOT/.venv/bin/python}" scripts/run_ns3_experiment.py "$@"
