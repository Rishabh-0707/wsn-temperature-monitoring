#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$WSN_ROOT"
if [[ -z "${WSN_PYTHON:-}" && -f .runtime/python-path && -z "${WSN_IGNORE_LOCAL_PYTHON:-}" ]]; then WSN_PYTHON="$(cat .runtime/python-path)"; fi
WSN_PYTHON="${WSN_PYTHON:-$WSN_ROOT/.venv/bin/python}"
[[ -x "$WSN_PYTHON" ]] || { echo 'Run bash scripts/setup.sh first.'; exit 1; }
PORT="${WSN_PORT:-8001}"
[[ -d frontend/dist ]] || (cd frontend && npm run build)
echo "Dashboard: http://127.0.0.1:$PORT/  | API: http://127.0.0.1:$PORT/docs"
exec "$WSN_PYTHON" -m uvicorn backend.app.main:app --host 127.0.0.1 --port "$PORT"
