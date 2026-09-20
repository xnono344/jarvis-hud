"""Tiny persistent briefing memory: one save_summary(), one load_summary()."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path


def _resolve_memory_file(memory_file: str | None = None) -> Path:
    if memory_file:
        raw = memory_file
    else:
        try:
            from backend.config import config

            raw = config.memory_file
        except Exception:
            raw = "backend/memory/memory.json"
    p = Path(os.path.expanduser(raw))
    if not p.is_absolute():
        # Resolve relative to the project root (parent of backend/)
        backend_dir = Path(__file__).resolve().parent.parent
        p = backend_dir.parent / raw
    return p


async def load_summary(memory_file: str | None = None) -> str:
    """Load the last-session summary, or empty string if none exists."""
    import aiofiles

    path = _resolve_memory_file(memory_file)
    if not path.exists():
        return ""
    try:
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            data = json.loads(await f.read())
        return str(data.get("summary", "") or "")
    except Exception:
        return ""


async def save_summary(summary: str, memory_file: str | None = None) -> str:
    """Save a short few-sentence summary of what happened this session."""
    import aiofiles

    path = _resolve_memory_file(memory_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"summary": summary.strip(), "updated": time.time()}
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(payload, indent=2))
    return f"saved summary to {path}"
