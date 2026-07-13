"""Hardware- and source-independent infrared code search engine."""

from __future__ import annotations

from datetime import UTC, datetime

from ..adapters.base import IRAdapter
from ..models.search_session import SearchSession, SearchStatus
from ..providers.base import CodeProvider


class SearchEngine:
    """Coordinate one search session across a code provider and IR adapter.

    The engine only depends on the contracts for a provider and an adapter.
    It has no knowledge of their concrete implementations or of Home Assistant.
    """

    def __init__(
        self,
        provider: CodeProvider,
        adapter: IRAdapter,
        session: SearchSession,
    ) -> None:
        """Initialize the engine with its code source, hardware, and state."""
        self.provider = provider
        self.adapter = adapter
        self.session = session

    async def start(self) -> None:
        """Load codes and mark the search session as running."""
        await self.provider.load()
        self.session.total_codes = self.provider.count()
        self.session.current_index = 0
        self.session.status = SearchStatus.RUNNING
        self.session.last_update = _utcnow()

        # TODO: Validate the selected device, brand, and command against the provider.

    async def send_current(self) -> str | None:
        """Send the provider's current code and return it when one exists."""
        code = self.provider.current()
        if code is None:
            return None

        await self.adapter.send_code(code)
        return code

    async def next(self) -> str | None:
        """Advance to, send, and return the next available code."""
        code = self.provider.next()
        if code is None:
            return None

        await self.adapter.send_code(code)
        self.session.next()
        return code

    async def previous(self) -> str | None:
        """Move back to, send, and return the previous available code."""
        code = self.provider.previous()
        if code is None:
            return None

        await self.adapter.send_code(code)
        self.session.previous()
        return code

    async def finish(self) -> None:
        """Mark the current search session as finished."""
        self.session.finish()
        # TODO: Persist or expose the completed search result.


def _utcnow() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(UTC)
