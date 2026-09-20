"""Single source of truth for backend configuration.

Loads secrets from `.env` (via python-dotenv) and non-secret settings from
`config.toml`. Every path, key, port, and model name must come from here —
nothing is hardcoded elsewhere.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

try:
    from dotenv import load_dotenv
except ImportError:

    def load_dotenv(*args, **kwargs):  # type: ignore[no-redef]
        return False


load_dotenv(_BACKEND_DIR / ".env")


def normalize_voice_rate(value: str | None, default: str = "+30%") -> str:
    """Normalize a voice speed into Edge-TTS rate form (``+30%`` = ~1.3x).

    Accepts multipliers (``1.3``, ``1.3x``) or percentages (``30``, ``30%``,
    ``+30%``). Clamps to -50%..+100% so a typo cannot produce chipmunk audio.
    """
    raw = str(value or "").strip().lower()
    if not raw:
        return default
    try:
        if raw.endswith("x"):
            pct = round((float(raw[:-1]) - 1.0) * 100)
        elif raw.endswith("%"):
            pct = round(float(raw[:-1]))
        else:
            number = float(raw)
            pct = round((number - 1.0) * 100) if number < 5 else round(number)
    except ValueError:
        return default
    pct = max(-50, min(100, pct))
    return f"{'+' if pct >= 0 else ''}{pct}%"


def _get(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


@dataclass
class Config:
    # LLM
    llm_provider: str = "gemini"
    gemini_enabled: bool = True
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_fallback_models: list = field(default_factory=list)
    universal_base_url: str = ""
    universal_api_key: str = ""
    universal_model: str = ""

    # Network
    backend_host: str = "127.0.0.1"
    backend_ws_port: int = 8765
    backend_http_port: int = 8766
    ws_path: str = "/ws"
    browser_origins: list[str] = field(default_factory=list)

    # Telemetry
    telemetry_interval_ms: int = 2000

    # Feature flags
    tools_enabled: list = field(default_factory=list)
    plugins_enabled: list = field(default_factory=list)
    skills_enabled: list = field(default_factory=list)

    # Application names only; no arguments or shell expressions.
    applications_allowed: list[str] = field(default_factory=list)

    # Files
    memory_file: str = "backend/memory/memory.json"
    notes_file: str = "~/notes.txt"

    # Plugins
    github_token: str = ""

    # Voice
    voice_enabled: bool = True
    voice_id: str = "en-GB-RyanNeural"
    voice_rate: str = "+40%"
    voice_reply_max_chars: int = 2000
    stt_model: str = "small.en"

    # Resolved paths (absolute)
    backend_dir: Path = _BACKEND_DIR
    project_dir: Path = _BACKEND_DIR.parent


def _load_toml() -> dict:
    path = _BACKEND_DIR / "config.toml"
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def load_config() -> Config:
    toml = _load_toml()
    backend_cfg = toml.get("backend", {})
    telemetry_cfg = toml.get("telemetry", {})
    tools_cfg = toml.get("tools", {})
    plugins_cfg = toml.get("plugins", {})
    skills_cfg = toml.get("skills", {})
    memory_cfg = toml.get("memory", {})

    return Config(
        llm_provider=_get("LLM_PROVIDER", "gemini").lower() or "gemini",
        gemini_enabled=_get("GEMINI_ENABLED", "true").lower() not in ("0", "false", "no", "off"),
        gemini_api_key=_get("GEMINI_API_KEY"),
        gemini_model=_get("GEMINI_MODEL", "gemini-2.0-flash") or "gemini-2.0-flash",
        gemini_fallback_models=[
            m.strip() for m in _get("GEMINI_FALLBACK_MODELS", "").split(",") if m.strip()
        ],
        universal_base_url=_get("UNIVERSAL_BASE_URL"),
        universal_api_key=_get("UNIVERSAL_API_KEY"),
        universal_model=_get("UNIVERSAL_MODEL"),
        backend_host=_get("BACKEND_HOST", str(backend_cfg.get("host", "127.0.0.1"))),
        backend_ws_port=int(_get("BACKEND_WS_PORT", str(backend_cfg.get("ws_port", 8765)))),
        backend_http_port=int(_get("BACKEND_HTTP_PORT", str(backend_cfg.get("http_port", 8766)))),
        ws_path=str(backend_cfg.get("ws_path", "/ws")),
        browser_origins=list(backend_cfg.get("browser_origins", [])),
        telemetry_interval_ms=int(telemetry_cfg.get("update_interval_ms", 2000)),
        tools_enabled=list(tools_cfg.get("enabled", [])),
        plugins_enabled=list(plugins_cfg.get("enabled", [])),
        skills_enabled=list(skills_cfg.get("enabled", [])),
        applications_allowed=list(toml.get("applications", {}).get("allowed", [])),
        memory_file=str(memory_cfg.get("file", "backend/memory/memory.json")),
        notes_file=str(memory_cfg.get("notes_file", "~/notes.txt")),
        github_token=_get("GITHUB_TOKEN"),
        voice_id=_get("VOICE_ID", "en-GB-RyanNeural") or "en-GB-RyanNeural",
        voice_rate=normalize_voice_rate(_get("VOICE_RATE", "+40%"), "+40%"),
        voice_enabled=_get("VOICE_ENABLED", "true").lower() not in ("0", "false", "no", "off"),
        voice_reply_max_chars=int(_get("VOICE_REPLY_MAX_CHARS", "2000") or 2000),
        stt_model=_get("STT_MODEL", "small.en") or "small.en",
    )


config = load_config()


def active_model(cfg: Config | None = None) -> str:
    cfg = cfg or config
    if cfg.llm_provider == "gemini":
        return cfg.gemini_model
    return cfg.universal_model
