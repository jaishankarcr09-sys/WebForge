#!/bin/bash
set -Eeuo pipefail

export BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
export PORT="${PORT:-3000}"

uvicorn --app-dir /app/backend app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup SIGTERM SIGINT EXIT

cd /app/frontend
npm start -- --hostname 0.0.0.0 --port "$PORT" &
FRONTEND_PID=$!

while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$FRONTEND_PID" 2>/dev/null; do
  sleep 1
done

exit 1
