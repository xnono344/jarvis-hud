"""Hand-registered plugins — three concrete entries, no dynamic loading."""

from __future__ import annotations

from backend.plugins import github_plugin, reddit_plugin, spotify_plugin

PLUGINS = {
    "spotify": spotify_plugin,
    "github": github_plugin,
    "reddit": reddit_plugin,
}


def plugin_schema() -> list[dict]:
    """LLM-visible plugin descriptions (surfaced inside the system prompt)."""
    return [
        {"name": name, "description": mod.DESCRIPTION}
        for name, mod in PLUGINS.items()
    ]
