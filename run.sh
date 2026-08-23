#!/usr/bin/env bash
# Bring up the APS frontend and backend dev servers with hot reload.
#   - Backend: uvicorn --reload  (FastAPI on :8000)
#   - Frontend: vite dev server  (HMR on :5173, proxies /api -> :8000)
#
# Usage:
#   ./run.sh          # start both; Ctrl-C stops both
#   ./run.sh -b       # backend only
#   ./run.sh -f       # frontend only

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
PORT_B="${BACKEND_PORT:-8000}"
PORT_F="${FRONTEND_PORT:-5173}"

start_backend() {
  echo "▶︎ Backend on http://localhost:${PORT_B} (hot reload)"
  cd "$BACKEND"
  if command -v uv >/dev/null 2>&1; then
    exec uv run uvicorn main:app --reload --host 0.0.0.0 --port "$PORT_B"
  else
    exec uvicorn main:app --reload --host 0.0.0.0 --port "$PORT_B"
  fi
}

start_frontend() {
  echo "▶︎ Frontend on http://localhost:${PORT_F} (HMR)"
  cd "$FRONTEND"
  exec npm run dev -- --host 0.0.0.0 --port "$PORT_F"
}

cleanup() {
  echo
  echo "Stopping dev servers…"
  [[ -n "${BACKEND_PID:-}" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  [[ -n "${FRONTEND_PID:-}" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

mode="${1:-both}"
case "$mode" in
  both)
    start_backend & BACKEND_PID=$!
    start_frontend & FRONTEND_PID=$!
    ;;
  -b)
    start_backend & BACKEND_PID=$!
    ;;
  -f)
    start_frontend & FRONTEND_PID=$!
    ;;
  *)
    echo "Unknown option: $mode (use -b for backend only, -f for frontend only)" >&2
    exit 1
    ;;
esac

wait