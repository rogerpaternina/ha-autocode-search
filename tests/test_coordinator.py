"""Tests for the Autocode Search coordinator."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from custom_components.autocode_search.coordinator import AutocodeSearchCoordinator
from custom_components.autocode_search.models.ir_code import IRCode
from custom_components.autocode_search.models.search_filter import SearchFilter
from custom_components.autocode_search.models.search_session import (
    SearchSession,
    SearchStatus,
)
from custom_components.autocode_search.providers.composite import (
    CompositeCodeProvider,
)
from tests.test_search_engine import FakeAdapter, FakeProvider


def _provider_codes(count: int) -> list[IRCode]:
    return [
        IRCode(name=f"code-{index}", payload=f"code-{index}")
        for index in range(1, count + 1)
    ]


def _create_coordinator() -> AutocodeSearchCoordinator:
    """Create a coordinator with minimal Home Assistant stubs."""
    hass = SimpleNamespace(data={})
    entry = SimpleNamespace(
        entry_id="entry-1",
        title="Autocode Search",
        data={"entity_id": "remote.living_room"},
        options={},
    )
    coordinator = AutocodeSearchCoordinator(hass, entry)  # type: ignore[arg-type]
    coordinator.async_set_updated_data = MagicMock()
    return coordinator


def _create_session() -> SearchSession:
    """Create a session for coordinator tests."""
    now = datetime.now(UTC)
    return SearchSession(
        session_id="session-1",
        device_type="tv",
        brand="lg",
        command="power",
        current_index=0,
        total_codes=0,
        status=SearchStatus.IDLE,
        started_at=None,
        last_update=now,
    )


def test_async_publish_session_updates_coordinator_data() -> None:
    """Coordinator publishes session progress to listeners."""
    coordinator = _create_coordinator()
    provider = FakeProvider(_provider_codes(2))
    adapter = FakeAdapter()
    session = _create_session()

    async def _run() -> None:
        await coordinator.async_start_search(provider, adapter, session)
        await coordinator.async_publish_session()

    asyncio.run(_run())

    assert coordinator.async_set_updated_data.call_count >= 1
    data = coordinator.async_set_updated_data.call_args_list[-1].args[0]
    assert data["search_status"] == SearchStatus.RUNNING.value
    assert data["codes_total"] == 2
    assert data["codes_after_filter"] == 2
    assert data["codes_tested"] == 0
    assert data["progress"] == 0.0


def test_coordinator_pause_resume_and_cancel_delegate_to_engine() -> None:
    """Coordinator control methods update the active session state."""
    coordinator = _create_coordinator()
    provider = FakeProvider(_provider_codes(3))
    adapter = FakeAdapter()
    session = _create_session()

    async def _run() -> None:
        engine = await coordinator.async_start_search(provider, adapter, session)
        await engine.send_current()
        await coordinator.async_pause_search()
        await coordinator.async_resume_search()
        await coordinator.async_cancel_search()

    asyncio.run(_run())

    assert coordinator.search_session.status is SearchStatus.CANCELLED
    assert coordinator.search_session.codes_tested == 1
    published = coordinator.async_set_updated_data.call_args_list[-1].args[0]
    assert published["cancelled"] is True
    assert published["paused"] is False


def test_coordinator_publishes_filter_metadata() -> None:
    """Coordinator publishes filter statistics from the active session."""
    coordinator = _create_coordinator()
    provider = FakeProvider(
        [
            IRCode(name="code-1", payload="code-1", manufacturer="LG"),
            IRCode(name="code-2", payload="code-2", manufacturer="LG"),
        ]
    )
    adapter = FakeAdapter()
    session = _create_session()
    search_filter = SearchFilter(manufacturer="LG")

    async def _run() -> None:
        await coordinator.async_start_search(provider, adapter, session, search_filter)

    asyncio.run(_run())

    published = coordinator.async_set_updated_data.call_args_list[-1].args[0]
    assert published["filter_summary"] == "LG"
    assert published["codes_after_filter"] == 2


def test_coordinator_publishes_composite_provider_statistics() -> None:
    """Composite provider statistics are copied to the session and published."""
    coordinator = _create_coordinator()
    composite = CompositeCodeProvider(
        [
            FakeProvider([IRCode(name="power", payload="p-1", protocol="NEC")]),
            FakeProvider(
                [
                    IRCode(name="power", payload="p-1", protocol="NEC"),
                    IRCode(name="mute", payload="p-2", protocol="NEC"),
                ]
            ),
        ]
    )
    adapter = FakeAdapter()
    session = _create_session()

    async def _run() -> None:
        await coordinator.async_start_search(composite, adapter, session)

    asyncio.run(_run())

    assert session.providers_used == ["Fake", "Fake"]
    assert session.duplicates_removed == 1
    published = coordinator.async_set_updated_data.call_args_list[-1].args[0]
    assert published["providers_used"] == ["Fake", "Fake"]
    assert published["providers_completed"] == ["Fake", "Fake"]
    assert published["duplicates_removed"] == 1


def test_coordinator_finish_search_publishes_finished_state() -> None:
    """Finishing through the coordinator exposes a finished session."""
    coordinator = _create_coordinator()
    provider = FakeProvider(_provider_codes(1))
    adapter = FakeAdapter()
    session = _create_session()

    async def _run() -> None:
        await coordinator.async_start_search(provider, adapter, session)
        await coordinator.async_finish_search()

    asyncio.run(_run())

    assert coordinator.search_session.status is SearchStatus.FINISHED
    published = coordinator.async_set_updated_data.call_args_list[-1].args[0]
    assert published["search_status"] == SearchStatus.FINISHED.value
    assert published["progress"] == 1.0
