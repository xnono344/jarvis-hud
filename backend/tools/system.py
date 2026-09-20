"""System tools: open_application, kill_process, system_control.

Wayland/Hyprland-native: hyprctl, wpctl (PipeWire volume), brightnessctl,
hyprlock/loginctl (lock), systemctl (shutdown/reboot).
"""

from __future__ import annotations

import asyncio
import re

from backend.config import config


async def _run(*args: str, timeout: int = 15) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise TimeoutError(f"timed out: {' '.join(args)}")
    return proc.returncode, (out or b"").decode("utf-8", errors="replace").strip()


async def open_application(params: dict) -> str:
    """Launch an application via Hyprland. Params: {name: app/command to launch}."""
    name = str(params.get("name", "")).strip()
    if not name:
        raise ValueError("name is empty")
    if name not in config.applications_allowed or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
        raise PermissionError("Application is not approved. Add its executable name to [applications].allowed; commands and arguments are not accepted.")
    code, out = await _run("hyprctl", "dispatch", "exec", name)
    if code != 0:
        raise RuntimeError(f"hyprctl failed: {out}")
    return f"launched: {name}" + (f" ({out})" if out else "")


async def kill_process(params: dict) -> str:
    """Kill a process by name or PID. Params: {name_or_pid}. DESTRUCTIVE: confirmed + re-verified by caller."""
    import signal

    target = str(params.get("name_or_pid", "")).strip()
    if not target:
        raise ValueError("name_or_pid is empty")
    if target.isdigit():
        import os

        os.kill(int(target), signal.SIGTERM)
        await asyncio.sleep(1.0)
        try:
            os.kill(int(target), 0)
            os.kill(int(target), signal.SIGKILL)
            return f"killed pid {target} (SIGKILL after SIGTERM)"
        except ProcessLookupError:
            return f"killed pid {target}"
    code, out = await _run("pkill", target)
    # pkill exit 1 = no processes matched; treat as informative, not fatal
    return f"pkill {target}: exit={code}" + (f" {out}" if out else "")


async def system_control(params: dict) -> str:
    """Control volume/brightness/lock/power. Params: {action, value?}.

    Actions: volume_up, volume_down, volume_set (value 0-100), mute, unmute,
    brightness_up, brightness_down, brightness_set (value 0-100),
    lock, shutdown, reboot. shutdown/reboot are DESTRUCTIVE.
    """
    action = str(params.get("action", "")).strip().lower()
    value = params.get("value")

    if action in ("volume_up", "volume_down"):
        delta = "+5%" if action == "volume_up" else "5%-"
        code, out = await _run("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", delta)
        if code != 0:
            raise RuntimeError(f"wpctl failed: {out}")
        return f"volume {action}: {out or 'ok'}"
    if action == "volume_set":
        pct = max(0, min(100, int(value)))
        code, out = await _run("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{pct}%")
        if code != 0:
            raise RuntimeError(f"wpctl failed: {out}")
        return f"volume set to {pct}%"
    if action in ("mute", "unmute"):
        code, out = await _run("wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "1" if action == "mute" else "0")
        if code != 0:
            raise RuntimeError(f"wpctl failed: {out}")
        return f"audio {action}d"
    if action in ("brightness_up", "brightness_down"):
        arg = "+5%" if action == "brightness_up" else "5%-"
        code, out = await _run("brightnessctl", "set", arg)
        if code != 0:
            raise RuntimeError(f"brightnessctl failed: {out}")
        return f"brightness {action}: {out or 'ok'}"
    if action == "brightness_set":
        pct = max(1, min(100, int(value)))
        code, out = await _run("brightnessctl", "set", f"{pct}%")
        if code != 0:
            raise RuntimeError(f"brightnessctl failed: {out}")
        return f"brightness set to {pct}%"
    if action == "lock":
        for cmd in (["hyprlock"], ["loginctl", "lock-session"]):
            try:
                code, out = await _run(*cmd)
                if code == 0:
                    return f"session locked via {' '.join(cmd)}"
            except FileNotFoundError:
                continue
        raise RuntimeError("no lock command available (tried hyprlock, loginctl)")
    if action == "shutdown":
        code, out = await _run("systemctl", "poweroff")
        if code != 0:
            raise RuntimeError(f"shutdown failed: {out}")
        return "shutting down"
    if action == "reboot":
        code, out = await _run("systemctl", "reboot")
        if code != 0:
            raise RuntimeError(f"reboot failed: {out}")
        return "rebooting"
    raise ValueError(
        f"unknown system_control action: {action!r} "
        "(volume_up/volume_down/volume_set/mute/unmute/brightness_up/brightness_down/brightness_set/lock/shutdown/reboot)"
    )
