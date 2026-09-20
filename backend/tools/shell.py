"""Shell tool: run_shell_command (DESTRUCTIVE — always confirmed + re-verified)."""

from __future__ import annotations

import asyncio

TIMEOUT_S = 60
MAX_OUTPUT = 8000


async def run_shell_command(params: dict) -> str:
    """Run a shell command and capture its output. Params: {cmd, cwd?: dir}. DESTRUCTIVE: confirmed before running."""
    import os

    cmd = str(params.get("cmd", "")).strip()
    if not cmd:
        raise ValueError("cmd is empty")
    cwd = params.get("cwd")
    cwd = os.path.expanduser(cwd) if cwd else None
    proc = await asyncio.create_subprocess_shell(
        cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_S)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise TimeoutError(f"command timed out after {TIMEOUT_S}s: {cmd}")
    text = (out or b"").decode("utf-8", errors="replace")
    if len(text) > MAX_OUTPUT:
        text = text[:MAX_OUTPUT] + f"\n...[truncated, {len(text)} chars total]"
    return f"exit={proc.returncode}\n{text}".strip()
