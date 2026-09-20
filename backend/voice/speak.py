"""Voice output — free TTS with the closest JARVIS-like British male voice.

Default voice `en-GB-RyanNeural` (Edge-TTS, no API key): calm, formal British
male — the community's standard free JARVIS substitute. Override with VOICE_ID
in backend/.env (e.g. en-GB-ThomasNeural). Speech speed defaults to +30% (~1.3x)
and can be tuned with VOICE_RATE in backend/.env (e.g. +30% or +50%). Not a 1:1 Paul Bettany clone — no
free model is — but the closest free out-of-box option.

Not wired into the chat loop yet: call speak()/speak_and_play() directly, or
wait for the speaking-state + audio-event wiring (see INTEGRATION.md §10).
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import uuid

DEFAULT_VOICE = "en-GB-RyanNeural"


def _voice_id(voice: str | None = None) -> str:
    if voice:
        return voice
    try:
        from backend.config import config

        return config.voice_id or DEFAULT_VOICE
    except Exception:
        return os.environ.get("VOICE_ID", DEFAULT_VOICE) or DEFAULT_VOICE


def _voice_rate(rate: str | None = None) -> str:
    try:
        from backend.config import normalize_voice_rate, config

        return normalize_voice_rate(rate or config.voice_rate, "+40%")
    except Exception:
        return normalize_voice_rate_fallback(rate)


def normalize_voice_rate_fallback(rate: str | None = None) -> str:
    raw = str(rate or os.environ.get("VOICE_RATE", "+40%")).strip().lower()
    if raw.endswith("x"):
        try:
            pct = round((float(raw[:-1]) - 1.0) * 100)
        except ValueError:
            return "+40%"
    elif raw.endswith("%"):
        try:
            pct = round(float(raw[:-1]))
        except ValueError:
            return "+40%"
    else:
        return "+40%"
    pct = max(-50, min(100, pct))
    return f"{'+' if pct >= 0 else ''}{pct}%"


async def speak(text: str, voice: str | None = None, rate: str | None = None, out_path: str | None = None) -> str:
    """Synthesize text to an MP3 file. Returns the file path."""
    import edge_tts

    text = (text or "").strip()
    if not text:
        raise ValueError("text is empty")
    if len(text) > 2000:
        text = text[:2000]
    dest = out_path or os.path.join(
        tempfile.gettempdir(), f"jarvis-speech-{os.getpid()}-{uuid.uuid4().hex}.mp3"
    )
    await edge_tts.Communicate(text, _voice_id(voice), rate=_voice_rate(rate)).save(dest)
    return dest


async def play(path: str) -> str:
    """Play an audio file via PipeWire (pw-play, falls back to paplay/mpg123)."""
    for cmd in (["pw-play", path], ["paplay", path], ["mpg123", "-q", path]):
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            _, err = await asyncio.wait_for(proc.communicate(), timeout=120)
            if proc.returncode == 0:
                return f"played {path} via {' '.join(cmd[:1])}"
        except FileNotFoundError:
            continue
    raise RuntimeError("no audio player available (tried pw-play, paplay, mpg123)")


async def speak_and_play(text: str, voice: str | None = None, rate: str | None = None) -> str:
    """Synthesize and immediately play through the default sink."""
    path = await speak(text, voice=voice, rate=rate)
    try:
        await play(path)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    return "spoken"
