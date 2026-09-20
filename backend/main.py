"""JARVIS backend entrypoint: loads config, starts WebSocket bridge + HTTP sidecar.

Run from the project root:
    python backend/main.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.bridge.server import BridgeServer
from backend.config import config
from backend.http_server import create_app
from backend.security import LocalAccess

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s: %(message)s")
# The SDK nags about manual tool calling on every request; our confirmation
# flow forbids auto-execution, so the advisory never applies. Errors still show.
logging.getLogger("google_genai").setLevel(logging.ERROR)
log = logging.getLogger("jarvis.main")


async def main() -> None:
    from websockets.asyncio.server import serve
    from aiohttp import web

    try:
        bridge = BridgeServer()  # raises if no LLM provider is configured
    except RuntimeError as e:
        log.error("%s", e)
        log.error("Fix backend/.env (see backend/.env.example) and restart.")
        raise SystemExit(1)
    names = [type(p).__name__ for p in bridge.providers]
    log.info("LLM chain: %s", " -> ".join(names))

    # max_size headroom: spoken replies (base64 MP3, up to ~2k chars) plus
    # mic uploads must never trip the default 1MB frame cap mid-session.
    access = LocalAccess()
    ws_server = await serve(
        bridge.handle_client,
        config.backend_host,
        config.backend_ws_port,
        max_size=8 * 1024 * 1024,
        process_request=access.process_ws_request,
        subprotocols=["jarvis"],
    )
    log.info("WebSocket: ws://%s:%d%s", config.backend_host, config.backend_ws_port, config.ws_path)

    app = create_app(broadcast=bridge.broadcast_event, access=access)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.backend_host, config.backend_http_port)
    await site.start()
    log.info("HTTP:      http://%s:%d", config.backend_host, config.backend_http_port)

    asyncio.create_task(bridge.broadcast_telemetry())
    await ws_server.wait_closed()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
