#!/usr/bin/env bash
# J.A.R.V.I.S mic toggle — bind this to any key in Hyprland, e.g:
#   bind = SUPER, M, exec, /absolute/path/to/jarvis-hud/jarvis-mic.sh
# Or to a dedicated mic key (find its name with `wev`, then press it):
#   bind = , XF86AudioMicMute, exec, /absolute/path/to/jarvis-hud/jarvis-mic.sh
# NOTE: a plain laptop "Fn" key sends no event to Linux (hardware-level), so it
# cannot be bound — use Fn+<key> combos, the mic key, or Super+M instead.
set -euo pipefail
cd "$(dirname "$0")"
exec backend/.venv/bin/python - <<'PYTHON'
import json
import urllib.request
from backend.config import config

host = "[::1]" if config.backend_host == "::1" else config.backend_host
base = f"http://{host}:{config.backend_http_port}"
with urllib.request.urlopen(base + "/api/session", timeout=5) as response:
    token = json.load(response)["token"]
request = urllib.request.Request(base + "/api/mic", method="POST", headers={"Authorization": "Bearer " + token})
with urllib.request.urlopen(request, timeout=5) as response:
    response.read()
PYTHON
