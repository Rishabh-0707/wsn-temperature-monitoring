#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$WSN_ROOT"
mkdir -p .runtime
[[ -d .venv ]] || python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.lock.txt
(cd frontend && npm ci --cache ../.runtime/npm-cache && npm run build)
if [[ -f "$CONTIKI/Makefile.include" ]]; then
  printf 'CONTIKI := %s\n' "$CONTIKI" > .runtime/contiki.mk
  echo "Using Contiki-NG at $CONTIKI"
else
  echo 'Set CONTIKI to an existing Contiki-NG checkout before running simulations.'
fi
python3 scripts/generate_simulations.py
echo 'Setup complete. Start the dashboard with: bash scripts/start_project.sh'
echo 'Then run an experiment with: bash scripts/run_experiment.sh 5'
