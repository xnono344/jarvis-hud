"""Reddit plugin — public JSON endpoints, read-only, no auth.

Primary: reddit.com public JSON (per spec). Reddit blocks some networks/IPs
with 403, so on failure we fall back to the public Arctic Shift archive API.
"""

from __future__ import annotations

NAME = "reddit"
DESCRIPTION = "Reddit public read-only API. Actions: top_posts. Params: {subreddit, limit?, time?}."
HEADERS = {"User-Agent": "jarvis-backend/1.0 (CachyOS; +local-assistant)"}
ARCTIC = "https://arctic-shift.photon-reddit.com/api/posts/search"


async def _from_reddit(client, subreddit: str, limit: int, time_filter: str) -> list[str] | None:
    try:
        resp = await client.get(
            f"https://www.reddit.com/r/{subreddit}/top.json",
            params={"limit": limit, "t": time_filter},
        )
        resp.raise_for_status()
        children = (resp.json().get("data") or {}).get("children", [])
        if not children:
            return None
        return [
            f"- {c.get('data', {}).get('title')} (▲{c.get('data', {}).get('score', 0)}, "
            f"{c.get('data', {}).get('num_comments', 0)} comments)"
            for c in children[:limit]
        ]
    except Exception:
        return None


async def _from_arctic(client, subreddit: str, limit: int) -> list[str] | None:
    try:
        resp = await client.get(
            ARCTIC, params={"subreddit": subreddit, "limit": limit, "sort": "desc"}
        )
        resp.raise_for_status()
        posts = (resp.json() or {}).get("data", [])
        if not posts:
            return None
        return [
            f"- {p.get('title')} (▲{p.get('score', 0)}, {p.get('num_comments', 0)} comments)"
            for p in posts[:limit]
        ]
    except Exception:
        return None


async def execute(action: str, params: dict) -> str:
    """Fetch top posts from a subreddit. Params: {subreddit, limit?: 1-25, time?: hour/day/week/month/year/all}."""
    import httpx

    action = (action or "").strip().lower()
    if action not in ("top_posts", "top", "hot"):
        raise ValueError(f"unknown reddit action: {action!r} (top_posts)")
    params = params or {}
    subreddit = str(params.get("subreddit", "")).strip().strip("/")
    if not subreddit:
        raise ValueError("top_posts needs {subreddit}")
    try:
        limit = max(1, min(25, int(params.get("limit", 5))))
    except (TypeError, ValueError):
        limit = 5
    time_filter = str(params.get("time", "day")).strip() or "day"
    async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
        lines = await _from_reddit(client, subreddit, limit, time_filter)
        if lines is None:
            lines = await _from_arctic(client, subreddit, limit)
    if not lines:
        return f"reddit r/{subreddit}: no posts found (both sources unreachable)"
    return f"top r/{subreddit} posts:\n" + "\n".join(lines)
