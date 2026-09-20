#!/usr/bin/env bash
# J.A.R.V.I.S final launcher — one command runs the whole app:
# built UI + API + WebSocket bridge. Open http://127.0.0.1:8766
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -f backend/.env ]; then
  echo "missing backend/.env — copy backend/.env.example and fill in keys" >&2
  exit 1
fi
if [ ! -d backend/.venv ]; then
  echo "missing backend/.venv — run: python3 -m venv backend/.venv && backend/.venv/bin/pip install -r backend/requirements.txt" >&2
  exit 1
fi
if [ ! -f dist/index.html ]; then
  echo "no production build — run: npm run build" >&2
  exit 1
fi

echo "J.A.R.V.I.S online — UI: http://127.0.0.1:8766 | WS: ws://127.0.0.1:8765"
exec backend/.venv/bin/python backend/main.py
