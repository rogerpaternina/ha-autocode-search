"""Service registration and handler tests for Autocode Search."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.autocode_search import services
from custom_components.autocode_search.coordinator import AutocodeSearchCoordinator
from custom_components.autocode_search.models.search_session import (
    SearchSession,
    SearchStatus,
)


def test_setup_registers_search_services() -> None:
    """All Autocode Search services are registered with Home Assistant."""
    hass = MagicMock()

    asyncio.run(services.async_setup_services(hass))

    assert hass.services.async_register.call_count == 7
    registered_services = {
        call.args[1] for call in hass.services.async_register.call_args_list
    }
    assert registered_services == {
        services.SERVICE_START_SEARCH,
        services.SERVICE_NEXT_CODE,
        services.SERVICE_PREVIOUS_CODE,
        services.SERVICE_FINISH_SEARCH,
        services.SERVICE_PAUSE,
        services.SERVICE_RESUME,
        services.SERVICE_CANCEL,
    }


def test_unload_removes_search_services() -> None:
    """All Autocode Search services are removed when the integration unloads."""
    hass = MagicMock()

    asyncio.run(services.async_unload_services(hass))

    assert hass.services.async_remove.call_count == 7


def _create_coordinator() -> AutocodeSearchCoordinator:
    """Create a coordinator stored in hass.data for service tests."""
    hass = SimpleNamespace(data={})
    entry = SimpleNamespace(
        entry_id="entry-1",
        title="Autocode Search",
        data={"provider": "auto"},
        options={},
    )
    coordinator = AutocodeSearchCoordinator(hass, entry)  # type: ignore[arg-type]
    coordinator.async_set_updated_data = AsyncMock()
    coordinator.async_publish_session = AsyncMock()
    return coordinator


def test_pause_resume_and_cancel_services_delegate_to_coordinator() -> None:
    """Session control services delegate to the coordinator."""
    coordinator = _create_coordinator()
    hass = SimpleNamespace(data={"autocode_search": {"entry-1": coordinator}})
    coordinator.async_pause_search = AsyncMock()
    coordinator.async_resume_search = AsyncMock()
    coordinator.async_cancel_search = AsyncMock()

    async def _run() -> None:
        await services._async_pause_search(hass, MagicMock())
        await services._async_resume_search(hass, MagicMock())
        await services._async_cancel_search(hass, MagicMock())

    asyncio.run(_run())

    coordinator.async_pause_search.assert_awaited_once()
    coordinator.async_resume_search.assert_awaited_once()
    coordinator.async_cancel_search.assert_awaited_once()


def test_start_search_publishes_session_updates() -> None:
    """Starting a search publishes coordinator session updates."""
    coordinator = _create_coordinator()
    hass = SimpleNamespace(
        data={"autocode_search": {"entry-1": coordinator}},
        services=SimpleNamespace(async_call=AsyncMock()),
    )
    now = datetime.now(UTC)
    session = SearchSession(
        session_id="session-1",
        device_type="tv",
        brand="lg",
        command="power",
        current_index=0,
        total_codes=1,
        status=SearchStatus.RUNNING,
        started_at=now,
        last_update=now,
        codes_tested=1,
    )
    engine = SimpleNamespace(
        session=session,
        send_current=AsyncMock(return_value="code-1"),
    )

    call = MagicMock()
    call.data = {
        "entity_id": "remote.living_room",
        "codes": ["code-1"],
        "device_type": "tv",
        "brand": "lg",
        "command": "power",
    }

    with (
        patch.object(
            coordinator,
            "async_start_search",
            AsyncMock(return_value=engine),
        ),
        patch(
            "custom_components.autocode_search.services.HomeAssistantRemoteAdapter",
            return_value=SimpleNamespace(),
        ),
    ):
        asyncio.run(services._async_start_search(hass, call))

    assert coordinator.async_publish_session.await_count >= 1
