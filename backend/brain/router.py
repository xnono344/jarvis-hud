"""Picks providers from config: primary first, the other as automatic failover.

LLM_PROVIDER selects the primary. If the other provider is also configured
(keys/URL + model present), it joins the chain — quota or outage on the
primary fails over silently instead of erroring to the user.
"""

from __future__ import annotations

from backend.brain.base import LLMProvider
from backend.brain.gemini_provider import GeminiProvider
from backend.brain.universal_provider import UniversalProvider
from backend.config import config


def _gemini_configured() -> bool:
    return bool(config.gemini_api_key) and config.gemini_enabled


def _universal_configured() -> bool:
    return bool(config.universal_base_url and config.universal_model)


def _gemini() -> GeminiProvider:
    return GeminiProvider(
        api_key=config.gemini_api_key,
        model=config.gemini_model,
        fallback_models=config.gemini_fallback_models,
    )


def _universal() -> UniversalProvider:
    return UniversalProvider(
        base_url=config.universal_base_url,
        api_key=config.universal_api_key,
        model=config.universal_model,
    )


def get_providers() -> list[LLMProvider]:
    """Primary first, configured secondary as failover. Raises if none usable."""
    chain: list[LLMProvider] = []
    if config.llm_provider == "gemini":
        if _gemini_configured():
            chain.append(_gemini())
        if _universal_configured():
            chain.append(_universal())
    else:
        if _universal_configured():
            chain.append(_universal())
        if _gemini_configured():
            chain.append(_gemini())
    if not chain:
        raise RuntimeError(
            "no LLM provider configured — set GEMINI_API_KEY or "
            "UNIVERSAL_BASE_URL + UNIVERSAL_MODEL in backend/.env"
        )
    return chain


def get_provider() -> LLMProvider:
    """Primary provider only (kept for tooling/tests)."""
    return get_providers()[0]
