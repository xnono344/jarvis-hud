"""Universal provider — OpenAI-compatible client.

Point it at NVIDIA NIM, Kilo gateway, OpenRouter, or plain OpenAI by changing
only .env values (UNIVERSAL_BASE_URL / UNIVERSAL_API_KEY / UNIVERSAL_MODEL).
"""

from __future__ import annotations

import json
from typing import Any

from backend.brain.base import LLMProvider


class UniversalProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str, model: str):
        self._base_url = base_url
        self._api_key = api_key
        self._model = model

    def _client(self):
        from openai import AsyncOpenAI

        kwargs: dict[str, Any] = {"api_key": self._api_key or "not-needed"}
        if self._base_url:
            kwargs["base_url"] = self._base_url
        return AsyncOpenAI(**kwargs)

    @staticmethod
    def _to_openai_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for m in messages:
            role = m.get("role", "user")
            if role == "tool":
                out.append(
                    {
                        "role": "tool",
                        "tool_call_id": m.get("tool_call_id", ""),
                        "content": str(m.get("content", "")),
                    }
                )
            elif role == "assistant" and m.get("tool_calls"):
                out.append(
                    {
                        "role": "assistant",
                        "content": str(m.get("content", "") or ""),
                        "tool_calls": [
                            {
                                "id": tc.get("id", ""),
                                "type": "function",
                                "function": {
                                    "name": tc.get("name", ""),
                                    "arguments": json.dumps(tc.get("arguments", {})),
                                },
                            }
                            for tc in m["tool_calls"]
                        ],
                    }
                )
            else:
                out.append({"role": role, "content": str(m.get("content", ""))})
        return out

    async def send(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        client = self._client()
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": self._to_openai_messages(messages),
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        response = await client.chat.completions.create(**kwargs)
        try:
            await client.close()
        except Exception:
            pass
        if not response.choices:
            return {"content": "", "tool_calls": []}
        choice = response.choices[0]
        msg = choice.message
        tool_calls: list[dict[str, Any]] = []
        for i, tc in enumerate(getattr(msg, "tool_calls", None) or []):
            try:
                args = json.loads(tc.function.arguments or "{}")
            except Exception:
                args = {}
            tool_calls.append({"id": tc.id or f"call_{i}", "name": tc.function.name, "arguments": args})
        return {"content": msg.content or "", "tool_calls": tool_calls}
