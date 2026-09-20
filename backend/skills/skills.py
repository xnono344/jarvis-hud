"""Skills: short named routines chaining a couple of tool calls each."""

from __future__ import annotations

import datetime
import os


def _require_dispatch(dispatch):
    if dispatch is None:
        raise PermissionError("This skill requires the bridge execution policy")


async def system_status(params: dict | None = None, *, dispatch=None) -> str:
    """Report CPU/RAM/battery. Params: {}."""
    import psutil

    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent
    lines = [f"CPU: {cpu:.0f}%", f"RAM: {ram:.0f}%"]
    try:
        battery = psutil.sensors_battery()
        if battery is not None:
            state = "charging" if battery.power_plugged else "on battery"
            lines.append(f"Battery: {battery.percent:.0f}% ({state})")
        else:
            lines.append("Battery: n/a (desktop)")
    except Exception:
        lines.append("Battery: n/a")
    return "system status:\n" + "\n".join(lines)


async def focus_mode(params: dict | None = None, *, dispatch=None) -> str:
    """Mute notifications (pause dunst/mako if present) + report open windows. Params: {}."""
    _require_dispatch(dispatch)

    muted = "notifications left as-is (no supported notification daemon control found)"
    for daemon in ("dunst", "mako"):
        try:
            if daemon == "dunst":
                await dispatch("run_shell_command", {"cmd": "dunstctl set-paused true"})
                muted = "notifications muted via dunst"
                break
            else:
                await dispatch("run_shell_command", {"cmd": "makoctl set-mode do-not-disturb"})
                muted = "notifications muted via mako (do-not-disturb)"
                break
        except PermissionError:
            raise
        except Exception:
            continue
    try:
        windows = await dispatch("window_management", {"action": "list"})
    except Exception as e:
        windows = f"(could not list windows: {e})"
    try:
        await dispatch("notify", {"title": "Focus mode", "message": "Focus mode on. Stay sharp."})
    except Exception:
        pass
    return f"focus mode on.\n{muted}\nopen windows:\n{windows}"


async def quick_note(params: dict | None = None, *, dispatch=None) -> str:
    """Append a timestamped line to the local notes file. Params: {text}."""
    _require_dispatch(dispatch)

    params = params or {}
    text = str(params.get("text", "")).strip()
    if not text:
        raise ValueError("quick_note needs {text}")
    try:
        from backend.config import config

        notes_file = os.path.expanduser(config.notes_file)
    except Exception:
        notes_file = os.path.expanduser("~/notes.txt")
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    await dispatch("write_file", {"path": notes_file, "content": f"[{stamp}] {text}\n", "append": True})
    return f"note saved to {notes_file}"


async def clean_downloads(params: dict | None = None, *, dispatch=None) -> str:
    """List files in ~/Downloads older than N days; each delete goes through the
    destructive confirmation flow before deleting. Params: {days?: default 30}.

    `dispatch` routes deletions through the bridge policy and confirmation gate.
    Without it, this routine only lists candidates and deletes nothing.
    """
    import time as _time

    params = params or {}
    try:
        days = max(1, int(params.get("days", 30)))
    except (TypeError, ValueError):
        days = 30
    downloads = os.path.expanduser("~/Downloads")
    if not os.path.isdir(downloads):
        return f"clean_downloads: {downloads} does not exist"
    cutoff = _time.time() - days * 86400
    candidates: list[tuple[str, float]] = []
    for entry in sorted(os.listdir(downloads)):
        full = os.path.join(downloads, entry)
        try:
            if os.path.isfile(full) and os.path.getmtime(full) < cutoff:
                candidates.append((full, os.path.getmtime(full)))
        except OSError:
            continue
    if not candidates:
        return f"clean_downloads: nothing in ~/Downloads older than {days} days"
    listing = "\n".join(
        f"- {path} ({datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')})"
        for path, mtime in candidates
    )
    if dispatch is None:
        return f"candidates older than {days} days (no confirm channel — deleted nothing):\n{listing}"
    deleted, skipped = [], []
    for path, _ in candidates:
        try:
            await dispatch("delete_file", {"path": path})
        except PermissionError as e:
            skipped.append(f"{path} ({e})")
            continue
        if not os.path.lexists(path):
            deleted.append(path)
        else:
            skipped.append(f"{path} (re-check FAILED, still exists)")
    report = [f"clean_downloads ({days}d): deleted {len(deleted)}, skipped {len(skipped)}."]
    if deleted:
        report.append("deleted:\n" + "\n".join(f"- {p}" for p in deleted))
    if skipped:
        report.append("skipped:\n" + "\n".join(f"- {p}" for p in skipped))
    return "\n".join(report)


async def daily_recap(params: dict | None = None, *, dispatch=None) -> str:
    """Combine saved memory summary + GitHub notifications + current Spotify track. Params: {}."""
    from backend.memory.memory import load_summary
    _require_dispatch(dispatch)

    memory = await load_summary()
    try:
        github = await dispatch("run_plugin", {"name": "github", "action": "list_notifications"})
    except Exception as e:
        github = f"(github unavailable: {e})"
    try:
        spotify = await dispatch("run_plugin", {"name": "spotify", "action": "current-track"})
    except Exception as e:
        spotify = f"(spotify unavailable: {e})"
    return (
        "daily recap:\n"
        f"memory: {memory or '(no previous session summary)'}\n\n"
        f"{github}\n\n"
        f"{spotify}"
    )
