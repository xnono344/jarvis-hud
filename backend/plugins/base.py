"""Plugin contract: a file exposing NAME, DESCRIPTION, and execute(action, params).

No dynamic loading, no marketplace — three concrete files registered by hand.
"""

from __future__ import annotations

from typing import Protocol


class Plugin(Protocol):
    NAME: str
    DESCRIPTION: str

    async def execute(self, action: str, params: dict) -> str: ...
