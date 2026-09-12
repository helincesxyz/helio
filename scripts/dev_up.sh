#!/usr/bin/env bash
# Convenience script: runs the backend API and the frontend dev server
# together. Ctrl-C stops both.
set -euo pipefail

cd "$(dirname "$0")/.."

(source backend/.venv/bin/activate && python -m helio.cli.main serve) &
BACKEND_PID=$!

(cd frontend && npm run dev) &
FRONTEND_PID=$!

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null' EXIT
wait
