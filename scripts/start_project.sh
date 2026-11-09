#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$WSN_ROOT"
[[ -x .venv/bin/python ]] || { echo 'Run bash scripts/setup.sh first.'; exit 1; }
PORT="${WSN_PORT:-8001}"
[[ -d frontend/dist ]] || (cd frontend && npm run build)
echo "Dashboard: http://127.0.0.1:$PORT/  | API: http://127.0.0.1:$PORT/docs"
exec .venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port "$PORT"
