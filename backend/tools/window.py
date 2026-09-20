"""Window management via `hyprctl dispatch` (Hyprland/Wayland-native)."""

from __future__ import annotations

import asyncio
import json


async def _hypr(*args: str, timeout: int = 15) -> str:
    proc = await asyncio.create_subprocess_exec(
        "hyprctl", *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise TimeoutError(f"hyprctl timed out: {' '.join(args)}")
    text = (out or b"").decode("utf-8", errors="replace").strip()
    if proc.returncode != 0:
        raise RuntimeError(f"hyprctl {' '.join(args)} failed: {text}")
    return text


async def window_management(params: dict) -> str:
    """Manage windows/workspaces via Hyprland. Params: {action, target?}.

    Actions: list (open windows), workspaces, focus (target: window/class/title),
    workspace (target: name/number to switch to), move_to_workspace (target: "window,workspace"),
    fullscreen, toggle_float, close. Examples: {action: focus, target: firefox},
    {action: workspace, target: "2"}.
    """
    action = str(params.get("action", "")).strip().lower()
    target = str(params.get("target", "")).strip()

    if action == "list":
        raw = await _hypr("clients", "-j")
        try:
            clients = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        lines = [
            f"{c.get('address')}  ws={c.get('workspace', {}).get('name')}  {c.get('class')} :: {c.get('title')}"
            for c in clients
        ]
        return "\n".join(lines) if lines else "(no windows)"
    if action == "workspaces":
        raw = await _hypr("workspaces", "-j")
        try:
            workspaces = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        return "\n".join(f"{w.get('id')}: {w.get('name')} ({w.get('windows')} windows)" for w in workspaces)
    if action == "focus":
        if not target:
            raise ValueError("focus needs {target: class/title}")
        return await _hypr("dispatch", "focuswindow", target)
    if action == "workspace":
        if not target:
            raise ValueError("workspace needs {target: name/number}")
        return await _hypr("dispatch", "workspace", target) or f"switched to workspace {target}"
    if action == "move_to_workspace":
        if not target:
            raise ValueError("move_to_workspace needs {target: 'window,workspace'}")
        window, _, workspace = target.partition(",")
        if not window.strip() or not workspace.strip():
            raise ValueError("target must look like 'firefox,2'")
        await _hypr("dispatch", "focuswindow", window.strip())
        return await _hypr("dispatch", "movetoworkspace", workspace.strip()) or f"moved to workspace {workspace.strip()}"
    if action == "fullscreen":
        return await _hypr("dispatch", "fullscreen", "0") or "fullscreen toggled"
    if action == "toggle_float":
        return await _hypr("dispatch", "togglefloating") or "floating toggled"
    if action == "close":
        if not target:
            return await _hypr("dispatch", "killactive") or "closed active window"
        await _hypr("dispatch", "focuswindow", target)
        return await _hypr("dispatch", "killactive") or f"closed {target}"
    raise ValueError(
        f"unknown window_management action: {action!r} "
        "(list/workspaces/focus/workspace/move_to_workspace/fullscreen/toggle_float/close)"
    )
