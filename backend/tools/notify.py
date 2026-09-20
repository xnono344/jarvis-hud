"""Desktop notification via notify-send."""

from __future__ import annotations

import asyncio


async def notify(params: dict) -> str:
    """Show a desktop notification. Params: {title, message}."""
    title = str(params.get("title", "J.A.R.V.I.S")).strip() or "J.A.R.V.I.S"
    message = str(params.get("message", "")).strip()
    if not message:
        raise ValueError("message is empty")
    proc = await asyncio.create_subprocess_exec(
        "notify-send", title, message,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _, err = await asyncio.wait_for(proc.communicate(), timeout=10)
    if proc.returncode != 0:
        raise RuntimeError(f"notify-send failed: {(err or b'').decode(errors='replace').strip()}")
    return f"notified: {title} — {message}"
