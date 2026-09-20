"""Shared LLM provider interface.

Both providers (Gemini, Universal) implement this one tiny contract so the
rest of the backend never cares which model is behind it.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


_RETRYABLE_SNIPPETS = (
    "429",
    "500",
    "502",
    "503",
    "504",
    "RESOURCE_EXHAUSTED",
    "UNAVAILABLE",
    "OVERLOADED",
    "DEADLINE_EXCEEDED",
    "INTERNAL",
    "CONNECTION",
    "TIMED OUT",
    "TIMEOUT",
)


def retryable(error: Exception) -> bool:
    """True when the failure is transient/quota-like and another provider or
    model is worth trying. Auth/validation errors fail fast."""
    text = f"{type(error).__name__}: {error}".upper()
    return any(s in text for s in _RETRYABLE_SNIPPETS)


class LLMProvider(ABC):
    @abstractmethod
    async def send(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """Send a conversation and optionally offer tools.

        Args:
            messages: list of {"role": "system"|"user"|"assistant", "content": str}
                plus optional {"role": "tool", "tool_call_id": str, "content": str}
            tools: OpenAI-style function schemas (or None for plain chat).

        Returns:
            {"content": str, "tool_calls": [{"id": str, "name": str, "arguments": dict}]}
            tool_calls is an empty list when the model answered directly.
        """
