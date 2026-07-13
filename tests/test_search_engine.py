"""Tests for the pure-Python infrared code search engine."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from custom_components.autocode_search.adapters.base import IRAdapter
from custom_components.autocode_search.engine.search_engine import SearchEngine
from custom_components.autocode_search.models.search_session import (
    SearchSession,
    SearchStatus,
)
from custom_components.autocode_search.providers.base import CodeProvider


class FakeProvider(CodeProvider):
    """Provide deterministic in-memory codes for engine tests."""

    def __init__(self, codes: list[str]) -> None:
        """Initialize the provider with a sequence of codes."""
        self._codes = codes
        self._index = 0
        self.loaded = False

    async def load(self) -> None:
        """Mark the provider as loaded and reset its cursor."""
        self.loaded = True
        self.reset()

    def current(self) -> str | None:
        """Return the code at the current cursor position."""
        if not self.loaded or not self._codes:
            return None
        return self._codes[self._index]

    def next(self) -> str | None:
        """Advance the cursor and return the next code."""
        if not self.loaded or self._index >= len(self._codes) - 1:
            return None
        self._index += 1
        return self.current()

    def previous(self) -> str | None:
        """Move the cursor back and return the previous code."""
        if not self.loaded or self._index == 0:
            return None
        self._index -= 1
        return self.current()

    def count(self) -> int:
        """Return the number of test codes."""
        return len(self._codes)

    def reset(self) -> None:
        """Reset the cursor to the first test code."""
        self._index = 0


class FakeAdapter(IRAdapter):
    """Capture infrared codes sent by the engine."""

    def __init__(self) -> None:
        """Initialize an empty sent-code history."""
        self.sent_codes: list[str] = []

    async def send_code(self, code: str) -> None:
        """Record an infrared code sent by the engine."""
        self.sent_codes.append(code)

    async def is_available(self) -> bool:
        """Return a stable available state for tests."""
        return True

    async def get_device_info(self) -> dict[str, str]:
        """Return non-sensitive fake adapter information."""
        return {"name": "Fake IR Adapter"}


def _create_engine() -> tuple[SearchEngine, FakeProvider, FakeAdapter, SearchSession]:
    """Create an engine with deterministic fake collaborators."""
    now = datetime.now(UTC)
    session = SearchSession(
        session_id="test-session",
        device_type="television",
        brand="test-brand",
        command="power",
        current_index=0,
        total_codes=0,
        status=SearchStatus.IDLE,
        started_at=now,
        last_update=now,
    )
    provider = FakeProvider(["code-1", "code-2", "code-3"])
    adapter = FakeAdapter()
    return SearchEngine(provider, adapter, session), provider, adapter, session


def test_start_loads_provider_and_starts_session() -> None:
    """The engine loads the provider and starts its session."""
    engine, provider, _, session = _create_engine()

    asyncio.run(engine.start())

    assert provider.loaded
    assert session.status is SearchStatus.RUNNING
    assert session.current_index == 0
    assert session.total_codes == 3


def test_next_sends_next_code_and_advances_session() -> None:
    """The engine sends the next provider code and advances the session."""
    engine, _, adapter, session = _create_engine()

    asyncio.run(engine.start())
    sent_code = asyncio.run(engine.next())

    assert sent_code == "code-2"
    assert adapter.sent_codes == ["code-2"]
    assert session.current_index == 1


def test_previous_sends_previous_code_and_rewinds_session() -> None:
    """The engine sends the previous provider code and rewinds the session."""
    engine, _, adapter, session = _create_engine()

    asyncio.run(engine.start())
    asyncio.run(engine.next())
    sent_code = asyncio.run(engine.previous())

    assert sent_code == "code-1"
    assert adapter.sent_codes == ["code-2", "code-1"]
    assert session.current_index == 0


def test_finish_marks_session_as_finished() -> None:
    """The engine marks the session as finished."""
    engine, _, _, session = _create_engine()

    asyncio.run(engine.start())
    asyncio.run(engine.finish())

    assert session.status is SearchStatus.FINISHED
    assert session.current_index == session.total_codes
