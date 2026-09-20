"""Filesystem tools: read_file, write_file, delete_file, list_directory."""

from __future__ import annotations

import os
from pathlib import Path


def _resolve(path: str) -> Path:
    return Path(os.path.expanduser(path)).resolve()


async def read_file(params: dict) -> str:
    """Read a text file from disk. Params: {path: file to read}."""
    import aiofiles

    target = _resolve(str(params.get("path", "")))
    async with aiofiles.open(target, "r", encoding="utf-8", errors="replace") as f:
        return await f.read()


async def write_file(params: dict) -> str:
    """Write (create or overwrite) a text file. Params: {path, content, append?: bool}."""
    import aiofiles

    target = _resolve(str(params.get("path", "")))
    content = str(params.get("content", ""))
    mode = "a" if params.get("append") else "w"
    if target.parent and not target.parent.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(target, mode, encoding="utf-8") as f:
        await f.write(content)
    action = "appended to" if mode == "a" else "wrote"
    return f"{action} {target} ({len(content)} chars)"


async def delete_file(params: dict) -> str:
    """Permanently delete a file or empty directory. Params: {path}. DESTRUCTIVE: confirmed + re-verified by caller."""
    raw = str(params.get("path", "")).strip()
    if not raw:
        raise ValueError("path is empty")
    # Resolve parents only: a final symlink is itself the deletion target.
    requested = Path(os.path.expanduser(raw))
    if requested.name in ("", ".", ".."):
        raise ValueError("refusing to delete a filesystem root or dot directory")
    target = requested.parent.resolve() / requested.name
    if not os.path.lexists(target):
        return f"nothing to delete: {target} does not exist"
    if target.is_symlink():
        target.unlink()
    elif target.is_dir():
        if any(target.iterdir()):
            raise ValueError(f"refusing to delete non-empty directory: {target}")
        target.rmdir()
    else:
        target.unlink()
    return f"deleted {target}"


async def list_directory(params: dict) -> str:
    """List files in a directory with sizes. Params: {path}."""
    target = _resolve(str(params.get("path", "")))
    if not target.is_dir():
        raise ValueError(f"not a directory: {target}")
    lines: list[str] = []
    for entry in sorted(target.iterdir(), key=lambda p: p.name.lower()):
        try:
            size = entry.stat().st_size if entry.is_file() else 0
            kind = "file" if entry.is_file() else "dir"
        except OSError:
            size, kind = 0, "?"
        lines.append(f"{kind:4} {size:>12}  {entry.name}")
    return "\n".join(lines) if lines else "(empty directory)"
