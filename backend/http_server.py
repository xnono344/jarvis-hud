"""HTTP sidecar: /api/* plus the built frontend (final app mode).

- /api/telemetry (same shape as the old Vite plugin), /api/health, /api/config.
- / serves the production build from ../dist (vite build) with SPA fallback,
  so one `python backend/main.py` runs the whole app: UI + API + WebSocket.
  If dist/ is missing (dev mode), only the API routes are served.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from aiohttp import web
from backend.security import LocalAccess

ACCESS = web.AppKey("access", LocalAccess)
BROADCAST = web.AppKey("broadcast", object)

try:
    from backend.bridge.protocol import mic_toggle
    from backend.bridge.server import get_system_metrics
    from backend.config import active_model, config
except ImportError:  # pragma: no cover
    from bridge.protocol import mic_toggle  # type: ignore[no-redef]
    from bridge.server import get_system_metrics  # type: ignore[no-redef]
    from config import active_model, config  # type: ignore[no-redef]


async def telemetry_handler(request: web.Request) -> web.Response:
    cpu, ram, gpu = await asyncio.to_thread(get_system_metrics)
    return web.json_response({"cpu": cpu, "ram": ram, "gpu": gpu})


async def health_handler(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def config_handler(request: web.Request) -> web.Response:
    # Safe subset only — never secrets.
    return web.json_response(
        {
            "llm_provider": config.llm_provider,
            "model": active_model(),
            "tools_enabled": config.tools_enabled,
            "plugins_enabled": config.plugins_enabled,
        }
    )


DIST_DIR = Path(__file__).resolve().parent.parent / "dist"
log = logging.getLogger("jarvis.http")


async def index_handler(request: web.Request) -> web.StreamResponse:
    return web.FileResponse(DIST_DIR / "index.html")


async def spa_fallback(request: web.Request) -> web.StreamResponse:
    """Unknown non-API path -> index.html (single-page app)."""
    if request.path.startswith("/api"):
        raise web.HTTPNotFound()
    return web.FileResponse(DIST_DIR / "index.html")


async def mic_handler(request: web.Request) -> web.Response:
    """Global-hotkey hook: tell every connected UI to toggle its mic."""
    broadcast = request.app.get(BROADCAST)
    if broadcast is None:
        return web.json_response({"status": "no-clients-channel"}, status=503)
    await broadcast(mic_toggle())
    return web.json_response({"status": "ok"})


@web.middleware
async def local_access_middleware(request, handler):
    access = request.app[ACCESS]
    if not access.request_allowed(request.headers):
        raise web.HTTPForbidden(text="Untrusted local origin or host")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        token = request.headers.get("Authorization", "").removeprefix("Bearer ")
        if not access.authenticated(token):
            raise web.HTTPUnauthorized(text="Local session credential required")
    if request.method == "OPTIONS":
        response = web.Response(status=204)
    else:
        response = await handler(request)
    origin = request.headers.get("Origin")
    if origin in access.origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


async def session_handler(request):
    response = web.json_response({
        "token": request.app[ACCESS].token,
        "ws_port": config.backend_ws_port,
        "ws_path": config.ws_path,
    })
    response.headers["Cache-Control"] = "no-store"
    return response


def create_app(broadcast=None, access=None) -> web.Application:
    app = web.Application(middlewares=[local_access_middleware])
    app[ACCESS] = access or LocalAccess()
    app[BROADCAST] = broadcast
    app.router.add_get("/api/session", session_handler)
    app.router.add_get("/api/telemetry", telemetry_handler)
    app.router.add_get("/api/health", health_handler)
    app.router.add_get("/api/config", config_handler)
    app.router.add_post("/api/mic", mic_handler)
    if (DIST_DIR / "index.html").exists():
        app.router.add_get("/", index_handler)
        assets = DIST_DIR / "assets"
        if assets.is_dir():
            app.router.add_static("/assets/", assets)
        for public_file in ("favicon.svg", "icons.svg"):
            if (DIST_DIR / public_file).exists():
                app.router.add_get(f"/{public_file}", _file(public_file))
        app.router.add_get("/{tail:.*}", spa_fallback)
        log.info("serving frontend from %s", DIST_DIR)
    else:
        log.info("no %s — API only (run `npm run build` for the full app)", DIST_DIR)
    return app


def _file(name: str):
    async def handler(request: web.Request) -> web.StreamResponse:
        return web.FileResponse(DIST_DIR / name)

    return handler
