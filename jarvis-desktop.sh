#!/usr/bin/env bash
# J.A.R.V.I.S native desktop app (Qt window, backend managed automatically).
set -euo pipefail
cd "$(dirname "$0")"
exec backend/.venv/bin/python backend/desktop/app.py "$@"
