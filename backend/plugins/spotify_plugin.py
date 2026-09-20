"""Spotify plugin — local playback via playerctl (MPRIS, no API key needed)."""

from __future__ import annotations

import asyncio

NAME = "spotify"
DESCRIPTION = "Control local Spotify playback via playerctl. Actions: play, pause, play_pause, next, previous, current-track, status."


async def _playerctl(*args: str, timeout: int = 10) -> str:
    proc = await asyncio.create_subprocess_exec(
        "playerctl", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise TimeoutError("playerctl timed out")
    text = (out or b"").decode("utf-8", errors="replace").strip()
    if proc.returncode != 0:
        detail = (err or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"playerctl {' '.join(args)} failed: {detail or 'no players found'}")
    return text


async def execute(action: str, params: dict) -> str:
    """Run a Spotify action. Params: {action, player?: player name}."""
    action = (action or "").strip().lower()
    player = str((params or {}).get("player", "spotify")).strip() or "spotify"
    base = ["-p", player]

    if action in ("play", "pause", "play_pause", "next", "previous", "stop"):
        cmd = "play-pause" if action == "play_pause" else action
        await _playerctl(*base, cmd)
        return f"spotify: {cmd}"
    if action in ("current-track", "current_track", "now-playing", "status"):
        try:
            artist = await _playerctl(*base, "metadata", "artist")
        except RuntimeError:
            artist = ""
        try:
            title = await _playerctl(*base, "metadata", "title")
        except RuntimeError:
            title = ""
        try:
            state = await _playerctl(*base, "status")
        except RuntimeError:
            state = "unknown"
        if not title and not artist:
            return "spotify: nothing playing (no player found)"
        return f"spotify [{state}]: {artist} — {title}".strip()
    raise ValueError(
        f"unknown spotify action: {action!r} (play/pause/play_pause/next/previous/stop/current-track)"
    )
