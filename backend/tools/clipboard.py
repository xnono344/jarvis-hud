"""Clipboard via wl-copy / wl-paste (Wayland-native). Read = safe, write = risky."""

from __future__ import annotations

import asyncio


async def clipboard(params: dict) -> str:
    """Read or write the Wayland clipboard. Params: {action: read|write, content?: text for write}."""
    action = str(params.get("action", "read")).strip().lower()
    if action == "read":
        proc = await asyncio.create_subprocess_exec(
            "wl-paste", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        out, err = await asyncio.wait_for(proc.communicate(), timeout=10)
        if proc.returncode != 0:
            raise RuntimeError(f"wl-paste failed: {(err or b'').decode(errors='replace').strip()}")
        text = (out or b"").decode("utf-8", errors="replace")
        return text if text else "(clipboard empty)"
    if action == "write":
        content = str(params.get("content", ""))
        proc = await asyncio.create_subprocess_exec(
            "wl-copy", stdin=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        _, err = await asyncio.wait_for(
            proc.communicate(content.encode("utf-8")), timeout=10
        )
        if proc.returncode != 0:
            raise RuntimeError(f"wl-copy failed: {(err or b'').decode(errors='replace').strip()}")
        return f"copied {len(content)} chars to clipboard"
    raise ValueError(f"unknown clipboard action: {action!r} (read|write)")
