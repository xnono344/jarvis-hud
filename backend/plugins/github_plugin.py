"""GitHub plugin — personal access token: notifications, repos, issues."""

from __future__ import annotations

import os

NAME = "github"
DESCRIPTION = "GitHub via personal access token. Actions: list_notifications, list_repos, create_issue."
API = "https://api.github.com"


def _token(params: dict) -> str:
    token = str((params or {}).get("token", "") or "").strip()
    if token:
        return token
    try:
        from backend.config import config

        token = (config.github_token or "").strip()
    except Exception:
        token = ""
    if not token:
        token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise ValueError("GitHub token missing: set GITHUB_TOKEN in backend/.env")
    return token


async def execute(action: str, params: dict) -> str:
    """Run a GitHub action. Params vary per action (see DESCRIPTION)."""
    import httpx

    action = (action or "").strip().lower()
    params = params or {}
    headers = {
        "Authorization": f"Bearer {_token(params)}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with httpx.AsyncClient(headers=headers, timeout=20) as client:
        if action == "list_notifications":
            resp = await client.get(f"{API}/notifications", params={"per_page": 10})
            resp.raise_for_status()
            items = resp.json()
            if not items:
                return "github: no unread notifications"
            lines = [f"- {n.get('subject', {}).get('title')} ({n.get('repository', {}).get('full_name')})" for n in items[:10]]
            return "github notifications:\n" + "\n".join(lines)
        if action == "list_repos":
            resp = await client.get(f"{API}/user/repos", params={"per_page": 10, "sort": "updated"})
            resp.raise_for_status()
            repos = resp.json()
            if not repos:
                return "github: no repos found"
            lines = [f"- {r.get('full_name')} ★{r.get('stargazers_count', 0)}" for r in repos[:10]]
            return "github repos:\n" + "\n".join(lines)
        if action == "create_issue":
            repo = str(params.get("repo", "")).strip()
            title = str(params.get("title", "")).strip()
            body = str(params.get("body", "")).strip()
            if not repo or "/" not in repo:
                raise ValueError("create_issue needs {repo: 'owner/name', title}")
            if not title:
                raise ValueError("create_issue needs a title")
            resp = await client.post(f"{API}/repos/{repo}/issues", json={"title": title, "body": body})
            resp.raise_for_status()
            issue = resp.json()
            return f"github: opened issue #{issue.get('number')} in {repo}: {issue.get('html_url')}"
    raise ValueError(f"unknown github action: {action!r} (list_notifications/list_repos/create_issue)")
