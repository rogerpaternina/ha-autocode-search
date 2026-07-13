"""Hardware- and source-independent infrared code search engine."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from ..adapters.base import IRAdapter
from ..models.ir_code import IRCode
from ..models.search_filter import SearchFilter
from ..models.search_session import SearchSession, SearchStatus
from ..providers.base import CodeProvider

_LOGGER = logging.getLogger(__name__)


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
        self._cancelled = False
        self._search_filter: SearchFilter | None = None

    async def start(self, search_filter: SearchFilter | None = None) -> None:
        """Load codes and mark the search session as running."""
        self._search_filter = search_filter
        async for _ in self.provider.iter_codes(search_filter):
            pass
        self.provider.reset()

        self._cancelled = False
        self.session.codes_total = self.provider.unfiltered_count()
        self.session.codes_after_filter = self.provider.count()
        self.session.total_codes = self.session.codes_after_filter
        self.session.current_index = 0
        self.session.codes_tested = 0
        self.session.filter_description = (
            search_filter.description()
            if search_filter is not None and search_filter.is_active()
            else "No filter"
        )
        self.session.filter_summary = (
            search_filter.summary()
            if search_filter is not None and search_filter.is_active()
            else "No filter"
        )
        self.session.status = SearchStatus.RUNNING
        self.session.started_at = _utcnow()
        self.session.finished_at = None
        self.session.last_update = _utcnow()
        _LOGGER.debug("Search started")

    async def send_current(self) -> str | None:
        """Send the provider's current code and return it when one exists."""
        if not self._can_send():
            return None

        await self._wait_while_paused()
        if not self._can_send():
            return None

        code = self.provider.current()
        if code is None:
            return None

        await self.adapter.send_code(code.payload)
        self._update_session_from_code(code, count_as_tested=True)
        self._log_progress(code)
        return code.payload

    async def next(self) -> str | None:
        """Advance to, send, and return the next available code."""
        if not self._can_send():
            return None

        await self._wait_while_paused()
        if not self._can_send():
            return None

        code = self.provider.next()
        if code is None:
            return None

        await self.adapter.send_code(code.payload)
        self.session.next()
        self._update_session_from_code(code, count_as_tested=True)
        self._log_progress(code)
        return code.payload

    async def previous(self) -> str | None:
        """Move back to, send, and return the previous available code."""
        if not self._can_send():
            return None

        await self._wait_while_paused()
        if not self._can_send():
            return None

        code = self.provider.previous()
        if code is None:
            return None

        await self.adapter.send_code(code.payload)
        self.session.previous()
        self._update_session_from_code(code, count_as_tested=False)
        self._log_current_code(code)
        return code.payload

    async def pause(self) -> None:
        """Pause the active search without changing its position."""
        self.session.pause()
        _LOGGER.debug("Search paused")

    async def resume(self) -> None:
        """Resume a paused search from its current position."""
        self.session.resume()
        _LOGGER.debug("Search resumed")

    async def cancel(self) -> None:
        """Cancel the active search and release provider resources."""
        self._cancelled = True
        self.session.cancel()
        self.provider.reset()
        _LOGGER.debug("Search cancelled")

    async def finish(self) -> None:
        """Mark the current search session as finished."""
        self.session.finish()
        _LOGGER.debug("Search finished")
        # TODO: Persist or expose the completed search result.

    async def run(self, search_filter: SearchFilter | None = None) -> None:
        """Iterate through every code while honoring pause and cancel controls."""
        if self.session.status is SearchStatus.IDLE:
            await self.start(search_filter)

        first_code = await self.send_current()
        if first_code is None:
            if self.session.status is SearchStatus.RUNNING:
                await self.finish()
            return

        while not self._cancelled:
            await self._wait_while_paused()
            if self._cancelled:
                break

            code = await self.next()
            if code is None:
                if self.session.status is SearchStatus.RUNNING:
                    await self.finish()
                break

    def _can_send(self) -> bool:
        """Return whether the engine may send another code."""
        return not self._cancelled and self.session.status is SearchStatus.RUNNING

    async def _wait_while_paused(self) -> None:
        """Block while the session remains paused and not cancelled."""
        while self.session.status is SearchStatus.PAUSED and not self._cancelled:
            await asyncio.sleep(0.05)

    def _update_session_from_code(self, code: IRCode, *, count_as_tested: bool) -> None:
        """Update session metadata from the code currently being tested."""
        self.session.update_current_code(code)
        if count_as_tested:
            self.session.record_forward_progress()

    def _log_progress(self, code: IRCode) -> None:
        """Emit debug logs for search progress and the active code."""
        _LOGGER.debug(
            "Progress %s/%s",
            self.session.codes_tested,
            self.session.codes_after_filter,
        )
        self._log_current_code(code)

    def _log_current_code(self, code: IRCode) -> None:
        """Emit debug logs for the active code metadata."""
        _LOGGER.debug("Current command: %s", code.name)
        if code.manufacturer is not None:
            _LOGGER.debug("Current manufacturer: %s", code.manufacturer)
        if code.model is not None:
            _LOGGER.debug("Current model: %s", code.model)


def _utcnow() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(UTC)
