"""Web search (read-only, no API key) via DuckDuckGo HTML endpoints."""

from __future__ import annotations

import re
from html import unescape

SEARCH_URL = "https://html.duckduckgo.com/html/"
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) jarvis-backend"}


async def web_search(params: dict) -> str:
    """Search the web and return short text results. Params: {query, count?: 1-10}."""
    import httpx

    query = str(params.get("query", "")).strip()
    if not query:
        raise ValueError("query is empty")
    try:
        count = max(1, min(10, int(params.get("count", 5))))
    except (TypeError, ValueError):
        count = 5
    async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
        resp = await client.post(SEARCH_URL, data={"q": query})
        resp.raise_for_status()
        html = resp.text
    blocks = re.findall(
        r'<a[^>]+class="result__a"[^>]*>(.*?)</a>.*?<a[^>]+class="result__snippet"[^>]*>(.*?)</a>'
        r"|<a[^>]+class=\"result__a\"[^>]*>(.*?)</a>",
        html,
        re.DOTALL,
    )
    results: list[str] = []
    for title, snippet, title_only in blocks[:count]:
        title_text = unescape(re.sub(r"<[^>]+>", "", title or title_only or "")).strip()
        snippet_text = unescape(re.sub(r"<[^>]+>", "", snippet or "")).strip()
        if title_text:
            results.append(f"- {title_text}" + (f"\n  {snippet_text}" if snippet_text else ""))
    if not results:
        # Fallback: strip any result titles at all
        titles = re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)[:count]
        for t in titles:
            clean = unescape(re.sub(r"<[^>]+>", "", t)).strip()
            if clean:
                results.append(f"- {clean}")
    if not results:
        return f"no results for: {query}"
    return f"results for '{query}':\n" + "\n".join(results)
