"""Speech-to-text — local faster-whisper, no API key, no cloud.

Default model `small.en` (~244MB, downloaded once to ~/.cache/huggingface):
good accuracy on CPU with low latency. Override with STT_MODEL in backend/.env
(tiny.en/base.en/small.en/medium.en, or multilingual small/medium).
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger("jarvis.voice")
_model = None
_model_name = None


def _model_id() -> str:
    try:
        from backend.config import config

        return config.stt_model or "small.en"
    except Exception:
        return os.environ.get("STT_MODEL", "small.en") or "small.en"


def _ensure_model():
    global _model, _model_name
    wanted = _model_id()
    if _model is None or _model_name != wanted:
        from faster_whisper import WhisperModel

        log.info("loading STT model %s (first run downloads it)", wanted)
        _model = WhisperModel(wanted, device="cpu", compute_type="int8")
        _model_name = wanted
    return _model


async def transcribe(path: str, language: str = "en") -> str:
    """Transcribe an audio file (mp3/wav/webm/opus) to text. Returns '' if nothing heard."""
    import asyncio

    model = _ensure_model()

    def _run():
        segments, _ = model.transcribe(path, language=language, beam_size=5)
        return " ".join(s.text for s in segments).strip()

    return await asyncio.to_thread(_run)
