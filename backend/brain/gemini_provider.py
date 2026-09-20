"""Gemini provider — calls the Gemini API directly (google-genai SDK).

Tries GEMINI_MODEL first, then each of GEMINI_FALLBACK_MODELS in order when
the failure looks transient (quota/429, overloaded/unavailable 5xx). Auth and
bad-request errors fail fast — retrying those is pointless.

Uses Gemini's native function calling: assistant turns carry `function_call`
parts, tool results are sent back as `function_response` parts on a user turn.
This is what makes multi-turn tool use actually work (a plain-text "TOOL RESULT"
hack silently breaks the call/result chain).
"""

from __future__ import annotations

import base64
import logging
from typing import Any

from backend.brain.base import LLMProvider, retryable as _retryable

log = logging.getLogger("jarvis.brain")


def _coerce_thought_signature(value: Any) -> bytes | None:
    """Normalize an opaque Gemini thought signature for SDK reuse.

    Invalid values are dropped rather than replaced: sending a fabricated
    signature would be worse than omitting one."""
    if value is None:
        return None
    if isinstance(value, bytes):
        return value or None
    if isinstance(value, (bytearray, memoryview)):
        return bytes(value) or None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return base64.b64decode(text, validate=True)
        except ValueError:
            return None
    return None


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str, fallback_models: list[str] | None = None):
        self._api_key = api_key
        self._models = [model] + [m for m in (fallback_models or []) if m and m != model]
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._api_key)
        return self._client

    @staticmethod
    def _build_contents(
        messages: list[dict[str, Any]], types: Any
    ) -> tuple[str, list[Any]]:
        """Translate the bridge's OpenAI-shaped history into Gemini Content objs.

        Returns (system_instruction, contents) where contents use native
        function_call / function_response parts so tool results chain correctly.
        Gemini thought signatures are preserved on rebuilt function_call parts.
        """
        system_parts: list[str] = []
        contents: list[Any] = []
        # Map tool_call_id -> function name so we can build function_response
        # parts on the user turn that follows a model's function_call.
        call_id_to_name: dict[str, str] = {}

        for m in messages:
            role = m.get("role", "user")
            content = str(m.get("content", ""))

            if role == "system":
                system_parts.append(content)
                continue

            if role == "assistant":
                tool_calls = m.get("tool_calls") or []
                for tc in tool_calls:
                    call_id_to_name[str(tc.get("id", ""))] = str(tc.get("name", ""))
                parts: list[Any] = []
                if content:
                    parts.append(types.Part.from_text(text=content or " "))
                for tc in tool_calls:
                    call_part = types.Part.from_function_call(
                        name=str(tc.get("name", "")),
                        args=dict(tc.get("arguments") or {}),
                    )
                    signature = _coerce_thought_signature(tc.get("thought_signature"))
                    if signature is not None:
                        call_part.thought_signature = signature
                    parts.append(call_part)
                if not parts:
                    parts.append(types.Part.from_text(text=" "))
                contents.append(types.Content(role="model", parts=parts))
                continue

            if role == "tool":
                name = call_id_to_name.get(str(m.get("tool_call_id", "")), "")
                if not name:
                    # No matching call recorded — fall back to a normal text turn.
                    contents.append(
                        types.Content(role="user", parts=[types.Part.from_text(text=f"[tool result]\n{content or ' '}")])
                    )
                else:
                    contents.append(
                        types.Content(
                            role="user",
                            parts=[
                                types.Part.from_function_response(
                                    name=name,
                                    response={"result": content or ""},
                                )
                            ],
                        )
                    )
                continue

            if content:
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=content or " ")]))
            else:
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text="(no input)")]))

        if not contents:
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text="(no input)")]))
        return "\n\n".join(system_parts), contents

    @staticmethod
    def _to_genai_tools(tools: list[dict[str, Any]] | None, types: Any):
        if not tools:
            return None
        declarations = []
        for t in tools:
            fn = t.get("function", t)
            declarations.append(
                types.FunctionDeclaration(
                    name=fn["name"],
                    description=fn.get("description", ""),
                    parameters_json_schema=fn.get("parameters") or {"type": "object", "properties": {}},
                )
            )
        return [types.Tool(function_declarations=declarations)]

    async def send(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        from google.genai import types

        client = self._ensure_client()
        system_instruction, contents = self._build_contents(messages, types)
        genai_tools = self._to_genai_tools(tools, types)
        last_error: Exception | None = None

        for name in self._models:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction or None,
                tools=genai_tools,
            )
            try:
                response = await client.aio.models.generate_content(
                    model=name, contents=contents, config=config
                )
                candidate_parts: list[Any] = []
                candidates = response.candidates or []
                if candidates and getattr(candidates[0], "content", None) is not None:
                    candidate_parts = getattr(candidates[0].content, "parts", None) or []
                tool_calls = []
                for i, part in enumerate(candidate_parts):
                    fc = getattr(part, "function_call", None)
                    if fc is None:
                        continue
                    tool_calls.append(
                        {
                            "id": getattr(fc, "id", None) or f"call_{i}",
                            "name": getattr(fc, "name", "") or "",
                            "arguments": dict(getattr(fc, "args", None) or {}),
                            "thought_signature": getattr(part, "thought_signature", None),
                        }
                    )
                # Read text parts directly: calling response.text logs a warning
                # whenever function_call parts are present.
                texts = [
                    part.text
                    for cand in (response.candidates or [])
                    for part in (getattr(cand.content, "parts", None) or [])
                    if getattr(part, "text", "")
                ]
                return {"content": "".join(texts).strip(), "tool_calls": tool_calls}
            except Exception as e:
                last_error = e
                if _retryable(e) and name != self._models[-1]:
                    log.warning("gemini %s failed (%s) — trying fallback", name, str(e)[:150])
                    continue
                raise
        raise last_error  # pragma: no cover - loop always raises first
