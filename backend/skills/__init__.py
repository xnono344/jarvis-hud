"""Hand-registered skills map."""

from __future__ import annotations

from backend.skills.skills import (
    clean_downloads,
    daily_recap,
    focus_mode,
    quick_note,
    system_status,
)

SKILLS = {
    "system_status": system_status,
    "focus_mode": focus_mode,
    "quick_note": quick_note,
    "clean_downloads": clean_downloads,
    "daily_recap": daily_recap,
}
