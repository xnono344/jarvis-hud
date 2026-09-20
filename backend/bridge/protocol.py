"""WebSocket protocol helpers — message types from INTEGRATION.md.

Frontend -> backend: chat:message, tool:confirm, audio:input (mic utterance)
Backend -> frontend: chat:response, chat:transcript, tool:call, tool:result,
                     status:change, telemetry:update, notification, audio:play,
                     mic:toggle (from POST /api/mic global hotkey)
"""

from __future__ import annotations

import json
import time


def chat_response(message_id: str, content: str, status: str = "idle") -> str:
    return json.dumps(
        {
            "type": "chat:response",
            "payload": {
                "message": {
                    "id": message_id,
                    "role": "assistant",
                    "content": content,
                    "timestamp": int(time.time() * 1000),
                },
                "status": status,
            },
        }
    )


def status_change(status: str) -> str:
    return json.dumps({"type": "status:change", "payload": {"status": status}})


def tool_result(call_id: str, result: str, error: str | None = None) -> str:
    return json.dumps(
        {
            "type": "tool:result",
            "payload": {"call_id": call_id, "result": result, "error": error},
        }
    )


def chat_transcript(message_id: str, text: str) -> str:
    """Echo transcribed mic speech so the frontend can show the user bubble."""
    return json.dumps(
        {
            "type": "chat:transcript",
            "payload": {
                "message": {
                    "id": message_id,
                    "role": "user",
                    "content": text,
                    "timestamp": int(time.time() * 1000),
                }
            },
        }
    )


def mic_toggle() -> str:
    """Ask every connected UI to toggle its mic (global-hotkey path)."""
    return json.dumps({"type": "mic:toggle", "payload": {}})


def audio_play(message_id: str, audio_b64: str, mime: str = "audio/mpeg") -> str:
    """Deliver synthesized reply audio for frontend playback."""
    return json.dumps(
        {
            "type": "audio:play",
            "payload": {"message_id": message_id, "audio": audio_b64, "mime": mime},
        }
    )


def telemetry_update(cpu: int, ram: int, gpu: int) -> str:
    return json.dumps(
        {"type": "telemetry:update", "payload": {"cpu": cpu, "ram": ram, "gpu": gpu}}
    )


def notification(title: str, message: str, level: str = "info") -> str:
    return json.dumps(
        {
            "type": "notification",
            "payload": {"title": title, "message": message, "level": level},
        }
    )


def parse_message(raw: str) -> tuple[str, dict]:
    """Return (type, payload) for an incoming frame; raises ValueError if malformed."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"not JSON: {e}")
    if not isinstance(data, dict) or "type" not in data:
        raise ValueError("message must be an object with a 'type' field")
    payload = data.get("payload", {})
    return str(data["type"]), payload if isinstance(payload, dict) else {}
