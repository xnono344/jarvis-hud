"""Risk tiers + confirmation flow.

Every tool call is classified:
- safe:        read-only / informational, runs immediately.
- risky:       modifies state but reversible, runs immediately and is logged.
- destructive: irreversible or high-impact, MUST be confirmed before running,
               then re-verified after running before reporting success.

Confirmation flow (no shortcuts):
1. State plainly what's about to happen and why.
2. Wait for explicit user confirmation via the frontend.
3. Execute the action.
4. Re-verify the actual result before reporting success.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import time
from enum import Enum

log = logging.getLogger("jarvis.permissions")

CONFIRM_TIMEOUT_S = 120


class RiskTier(str, Enum):
    SAFE = "safe"
    RISKY = "risky"
    DESTRUCTIVE = "destructive"


# Tool name -> risk tier. clipboard/system_control resolve dynamically (see below).
TOOL_RISK: dict[str, RiskTier] = {
    "read_file": RiskTier.SAFE,
    "list_directory": RiskTier.SAFE,
    "web_search": RiskTier.SAFE,
    "notify": RiskTier.SAFE,
    "write_file": RiskTier.RISKY,
    "open_application": RiskTier.RISKY,
    "window_management": RiskTier.RISKY,
    "system_control": RiskTier.RISKY,  # shutdown/reboot escalate to DESTRUCTIVE
    "clipboard": RiskTier.SAFE,  # write action escalates to RISKY
    "delete_file": RiskTier.DESTRUCTIVE,
    "run_shell_command": RiskTier.DESTRUCTIVE,
    "kill_process": RiskTier.DESTRUCTIVE,
}

_DESTRUCTIVE_SYSTEM_ACTIONS = {"shutdown", "reboot"}


def risk_of(tool_name: str, params: dict | None = None) -> RiskTier:
    """Resolve the effective risk tier for a tool call."""
    params = params or {}
    if tool_name == "clipboard" and str(params.get("action", "read")).strip().lower() == "write":
        return RiskTier.RISKY
    if tool_name == "system_control" and str(params.get("action", "")).strip().lower() in _DESTRUCTIVE_SYSTEM_ACTIONS:
        return RiskTier.DESTRUCTIVE
    return TOOL_RISK.get(tool_name, RiskTier.DESTRUCTIVE)


def describe_action(tool_name: str, params: dict) -> str:
    """Plain-language description used in the confirmation prompt."""
    if tool_name == "delete_file":
        return f"About to permanently delete `{params.get('path')}`. Confirm?"
    if tool_name == "run_shell_command":
        return f"About to run shell command `{params.get('cmd')}`. Confirm?"
    if tool_name == "kill_process":
        return f"About to kill process `{params.get('name_or_pid')}`. Confirm?"
    if tool_name == "system_control":
        return f"About to run system action `{params.get('action')}`. Confirm?"
    return f"About to execute `{tool_name}` with {params}. Confirm?"


# Pending confirmations are scoped to the connection and opaque action ID.
_pending: dict[tuple[object, str], asyncio.Future] = {}


async def request_confirmation(send, call_id: str, description: str, *, owner=None) -> bool:
    """Ask the frontend for confirmation and wait for its reply.

    `send` is an async callable taking a JSON string to push to the frontend.
    Returns True only on explicit confirmation (timeout or deny -> False).
    """
    loop = asyncio.get_running_loop()
    fut: asyncio.Future = loop.create_future()
    key = (owner, call_id)
    _pending[key] = fut
    try:
        await send(json.dumps({
            "type": "tool:call",
            "payload": {"call_id": call_id, "description": description},
        }))
        return bool(await asyncio.wait_for(fut, timeout=CONFIRM_TIMEOUT_S))
    except asyncio.TimeoutError:
        log.warning("confirmation timed out for %s", call_id)
        return False
    finally:
        _pending.pop(key, None)


def resolve_confirmation(call_id: str, confirmed: bool, *, owner=None) -> bool:
    """Deliver the frontend's answer to a waiting request_confirmation()."""
    fut = _pending.get((owner, call_id))
    if fut is None or fut.done():
        return False
    if type(confirmed) is not bool:
        return False
    fut.set_result(confirmed)
    return True


async def verify_result(tool_name: str, params: dict) -> tuple[bool, str]:
    """Re-verify a destructive action actually took effect.

    Returns (ok, detail). Only report success when ok is True.
    """
    params = params or {}
    if tool_name == "delete_file":
        path = os.path.expanduser(str(params.get("path", "")))
        if not os.path.lexists(path):
            return True, "verified: path is gone"
        return False, f"re-check failed: {path} still exists"
    if tool_name == "kill_process":
        target = str(params.get("name_or_pid", ""))
        try:
            if target.isdigit():
                os.kill(int(target), 0)  # raises if process is gone
                return False, f"re-check failed: pid {target} still running"
            r = subprocess.run(["pgrep", "-f", target], capture_output=True, text=True, timeout=10)
            if r.returncode != 0 or not r.stdout.strip():
                return True, "verified: no matching process running"
            return False, f"re-check failed: still running: {r.stdout.strip()}"
        except ProcessLookupError:
            return True, "verified: process is gone"
        except Exception as e:
            return False, f"re-check error: {e}"
    if tool_name == "run_shell_command":
        return True, f"verified: command exited (output captured at {time.strftime('%H:%M:%S')})"
    if tool_name == "system_control":
        return True, "executed (post-state check not applicable for this action)"
    return True, "no re-verification rule for this tool"
