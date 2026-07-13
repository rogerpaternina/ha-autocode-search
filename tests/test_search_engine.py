"""Tests for the pure-Python infrared code search engine."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from custom_components.autocode_search.adapters.base import IRAdapter
from custom_components.autocode_search.engine.search_engine import SearchEngine
from custom_components.autocode_search.models.ir_code import IRCode
from custom_components.autocode_search.models.search_filter import SearchFilter
from custom_components.autocode_search.models.search_session import (
    InvalidStateTransitionError,
    SearchSession,
    SearchStatus,
)
from custom_components.autocode_search.providers.base import CodeProvider
from custom_components.autocode_search.providers.filtering import filter_codes


class FakeProvider(CodeProvider):
    """Provide deterministic in-memory codes for engine tests."""

    def __init__(self, codes: list[IRCode]) -> None:
        """Initialize the provider with a sequence of codes."""
        self._all_codes = codes
        self._active_codes: list[IRCode] = []
        self._index = 0
        self.loaded = False

    async def load(self, search_filter: SearchFilter | None = None) -> None:
        """Mark the provider as loaded and apply the optional filter."""
        self.loaded = True
        self._active_codes = filter_codes(self._all_codes, search_filter)
        self.reset()

    def current(self) -> IRCode | None:
        """Return the code at the current cursor position."""
        if not self.loaded or not self._active_codes:
            return None
        return self._active_codes[self._index]

    def next(self) -> IRCode | None:
        """Advance the cursor and return the next code."""
        if not self.loaded or self._index >= len(self._active_codes) - 1:
            return None
        self._index += 1
        return self.current()

    def previous(self) -> IRCode | None:
        """Move the cursor back and return the previous code."""
        if not self.loaded or self._index == 0:
            return None
        self._index -= 1
        return self.current()

    def count(self) -> int:
        """Return the number of active test codes."""
        return len(self._active_codes)

    def unfiltered_count(self) -> int:
        """Return the number of test codes before filtering."""
        return len(self._all_codes)

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
        started_at=None,
        last_update=now,
    )
    provider = FakeProvider(
        [
            IRCode(name="power", payload="code-1", manufacturer="LG", device_type="tv"),
            IRCode(
                name="power",
                payload="code-2",
                manufacturer="Samsung",
                device_type="tv",
            ),
            IRCode(
                name="volume", payload="code-3", manufacturer="LG", device_type="tv"
            ),
        ]
    )
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
    assert session.codes_total == 3
    assert session.codes_after_filter == 3
    assert session.codes_tested == 0
    assert session.started_at is not None


def test_send_current_updates_progress_and_metadata() -> None:
    """Sending the current code records progress and metadata."""
    engine, _, adapter, session = _create_engine()

    asyncio.run(engine.start())
    sent_code = asyncio.run(engine.send_current())

    assert sent_code == "code-1"
    assert adapter.sent_codes == ["code-1"]
    assert session.codes_tested == 1
    assert session.current_code == "power"
    assert session.current_manufacturer == "LG"
    assert session.progress == pytest.approx(1 / 3)


def test_next_sends_next_code_and_advances_session() -> None:
    """The engine sends the next provider code and advances the session."""
    engine, _, adapter, session = _create_engine()

    asyncio.run(engine.start())
    asyncio.run(engine.send_current())
    sent_code = asyncio.run(engine.next())

    assert sent_code == "code-2"
    assert adapter.sent_codes == ["code-1", "code-2"]
    assert session.current_index == 1
    assert session.codes_tested == 2


def test_previous_sends_previous_code_and_rewinds_session() -> None:
    """The engine sends the previous provider code and rewinds the session."""
    engine, _, adapter, session = _create_engine()

    asyncio.run(engine.start())
    asyncio.run(engine.send_current())
    asyncio.run(engine.next())
    sent_code = asyncio.run(engine.previous())

    assert sent_code == "code-1"
    assert adapter.sent_codes == ["code-1", "code-2", "code-1"]
    assert session.current_index == 0
    assert session.codes_tested == 2


def test_pause_blocks_sending_until_resume() -> None:
    """Paused searches do not send new codes until they are resumed."""
    engine, _, adapter, session = _create_engine()

    async def _run() -> None:
        await engine.start()
        await engine.send_current()
        await engine.pause()
        blocked = await engine.next()
        await engine.resume()
        resumed = await engine.next()

        assert blocked is None
        assert resumed == "code-2"

    asyncio.run(_run())

    assert session.status is SearchStatus.RUNNING
    assert adapter.sent_codes == ["code-1", "code-2"]


def test_cancel_stops_search_and_blocks_further_sends() -> None:
    """Cancelled searches stop immediately and reject new sends."""
    engine, provider, adapter, session = _create_engine()

    async def _run() -> None:
        await engine.start()
        await engine.send_current()
        await engine.cancel()
        blocked = await engine.next()

        assert blocked is None

    asyncio.run(_run())

    assert session.status is SearchStatus.CANCELLED
    assert provider._index == 0
    assert adapter.sent_codes == ["code-1"]


def test_finish_marks_session_as_finished() -> None:
    """The engine marks the session as finished."""
    engine, _, _, session = _create_engine()

    asyncio.run(engine.start())
    asyncio.run(engine.finish())

    assert session.status is SearchStatus.FINISHED
    assert session.current_index == session.total_codes
    assert session.codes_tested == session.total_codes


def test_run_iterates_until_finish() -> None:
    """Automatic search execution finishes after testing every code."""
    engine, _, adapter, session = _create_engine()

    asyncio.run(engine.run())

    assert session.status is SearchStatus.FINISHED
    assert session.codes_tested == 3
    assert adapter.sent_codes == ["code-1", "code-2", "code-3"]


def test_run_respects_cancel() -> None:
    """Automatic search execution stops when cancelled."""
    engine, _, adapter, session = _create_engine()

    async def _run() -> None:
        await engine.start()
        await engine.send_current()
        await engine.cancel()
        await engine.run()

    asyncio.run(_run())

    assert session.status is SearchStatus.CANCELLED
    assert adapter.sent_codes == ["code-1"]


def test_start_applies_search_filter_statistics() -> None:
    """Starting a search records unfiltered and filtered code totals."""
    engine, _, _, session = _create_engine()
    search_filter = SearchFilter(manufacturer="LG", command="power")

    asyncio.run(engine.start(search_filter))

    assert session.codes_total == 3
    assert session.codes_after_filter == 1
    assert session.total_codes == 1
    assert session.filter_summary == "LG | POWER"


def test_pause_from_idle_raises() -> None:
    """Pause cannot be triggered before the search starts."""
    engine, _, _, _ = _create_engine()

    with pytest.raises(InvalidStateTransitionError):
        asyncio.run(engine.pause())
