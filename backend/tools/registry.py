"""Registers all 12 tools + their risk tier + LLM function schemas."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from backend.permissions import RiskTier, risk_of
from backend.tools import filesystem, shell, system, window, clipboard, notify, web

ToolFn = Callable[[dict], Awaitable[str]]


def _schema(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }


def _str(desc: str) -> dict[str, Any]:
    return {"type": "string", "description": desc}


TOOLS: dict[str, tuple[ToolFn, RiskTier, dict[str, Any]]] = {
    "read_file": (
        filesystem.read_file,
        RiskTier.SAFE,
        _schema("read_file", filesystem.read_file.__doc__ or "Read a file",
                {"path": _str("File path to read")}, ["path"]),
    ),
    "write_file": (
        filesystem.write_file,
        RiskTier.RISKY,
        _schema("write_file", filesystem.write_file.__doc__ or "Write a file",
                {"path": _str("File path to write"), "content": _str("Content to write"),
                 "append": {"type": "boolean", "description": "Append instead of overwrite"}}, ["path", "content"]),
    ),
    "delete_file": (
        filesystem.delete_file,
        RiskTier.DESTRUCTIVE,
        _schema("delete_file", filesystem.delete_file.__doc__ or "Delete a file",
                {"path": _str("File or empty directory to delete")}, ["path"]),
    ),
    "list_directory": (
        filesystem.list_directory,
        RiskTier.SAFE,
        _schema("list_directory", filesystem.list_directory.__doc__ or "List a directory",
                {"path": _str("Directory path to list")}, ["path"]),
    ),
    "run_shell_command": (
        shell.run_shell_command,
        RiskTier.DESTRUCTIVE,
        _schema("run_shell_command", shell.run_shell_command.__doc__ or "Run a shell command",
                {"cmd": _str("Shell command to run"), "cwd": _str("Working directory (optional)")}, ["cmd"]),
    ),
    "open_application": (
        system.open_application,
        RiskTier.RISKY,
        _schema("open_application", system.open_application.__doc__ or "Launch an app",
                {"name": _str("Application/command to launch")}, ["name"]),
    ),
    "kill_process": (
        system.kill_process,
        RiskTier.DESTRUCTIVE,
        _schema("kill_process", system.kill_process.__doc__ or "Kill a process",
                {"name_or_pid": _str("Process name or PID")}, ["name_or_pid"]),
    ),
    "system_control": (
        system.system_control,
        RiskTier.RISKY,
        _schema("system_control", system.system_control.__doc__ or "Control system",
                {"action": _str("volume_up/volume_down/volume_set/mute/unmute/brightness_up/brightness_down/brightness_set/lock/shutdown/reboot"),
                 "value": _str("Numeric value for set actions (optional)")}, ["action"]),
    ),
    "window_management": (
        window.window_management,
        RiskTier.RISKY,
        _schema("window_management", window.window_management.__doc__ or "Manage windows",
                {"action": _str("list/workspaces/focus/workspace/move_to_workspace/fullscreen/toggle_float/close"),
                 "target": _str("Target window/workspace (optional)")}, ["action"]),
    ),
    "clipboard": (
        clipboard.clipboard,
        RiskTier.SAFE,
        _schema("clipboard", clipboard.clipboard.__doc__ or "Clipboard access",
                {"action": _str("read or write"), "content": _str("Text to copy (write only)")}, ["action"]),
    ),
    "notify": (
        notify.notify,
        RiskTier.SAFE,
        _schema("notify", notify.notify.__doc__ or "Show a notification",
                {"title": _str("Notification title"), "message": _str("Notification body")}, ["message"]),
    ),
    "web_search": (
        web.web_search,
        RiskTier.SAFE,
        _schema("web_search", web.web_search.__doc__ or "Search the web",
                {"query": _str("Search query"), "count": _str("Max results 1-10 (optional)")}, ["query"]),
    ),
}

assert len(TOOLS) == 12, f"expected exactly 12 tools, got {len(TOOLS)}"


def get_tool_schema(enabled: list[str] | None = None) -> list[dict[str, Any]]:
    """Return OpenAI-style function schemas for enabled tools."""
    if enabled is not None:
        allowed = set(enabled)
        return [schema for name, (_, _, schema) in TOOLS.items() if name in allowed]
    return [schema for (_, _, schema) in TOOLS.values()]


def effective_risk(tool_name: str, params: dict | None = None) -> RiskTier:
    """Registry tier, refined by risk_of() for dynamic tools (clipboard/system_control)."""
    base = TOOLS[tool_name][1] if tool_name in TOOLS else RiskTier.DESTRUCTIVE
    dynamic = risk_of(tool_name, params)
    order = [RiskTier.SAFE, RiskTier.RISKY, RiskTier.DESTRUCTIVE]
    return dynamic if order.index(dynamic) >= order.index(base) else base
