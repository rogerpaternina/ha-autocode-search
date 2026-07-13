"""Integration tests for persisted success memory."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

from custom_components.autocode_search import services
from custom_components.autocode_search.coordinator import AutocodeSearchCoordinator
from custom_components.autocode_search.memory.models import SuccessRecord


def _entry() -> SimpleNamespace:
    return SimpleNamespace(
        entry_id="entry-1",
        title="Autocode Search",
        data={},
        options={},
    )


def _hass() -> SimpleNamespace:
    tasks: list[object] = []

    def async_create_task(coro: object) -> object:
        tasks.append(coro)
        return coro

    hass = SimpleNamespace(data={}, async_create_task=async_create_task)
    hass._tasks = tasks
    return hass


async def _run_pending_tasks(hass: SimpleNamespace) -> None:
    while hass._tasks:
        await hass._tasks.pop(0)


def _record() -> SuccessRecord:
    return SuccessRecord(
        manufacturer="LG",
        model="OLED55",
        device_type="tv",
        command="power",
        provider="SmartIR",
        protocol="NEC",
        payload="JgBQAAAB",
        last_used=datetime(2026, 7, 13, 12, 0, tzinfo=UTC),
        use_count=2,
    )


def test_coordinator_loads_success_memory_on_first_refresh() -> None:
    """Coordinator startup restores persisted successes and publishes them."""
    hass = _hass()
    coordinator = AutocodeSearchCoordinator(hass, _entry())  # type: ignore[arg-type]
    coordinator.async_set_updated_data = AsyncMock()

    async def _run() -> None:
        await coordinator.storage_backend.async_save([_record()])
        await coordinator.async_config_entry_first_refresh()

    asyncio.run(_run())

    assert coordinator.success_memory.count() == 1
    assert coordinator.data["success_count"] == 1
    assert coordinator.data["last_success"] == "LG OLED55 POWER"


def test_restart_reload_preserves_success_memory() -> None:
    """A new coordinator instance reloads records saved by a previous instance."""
    hass = _hass()

    async def _run() -> None:
        first = AutocodeSearchCoordinator(hass, _entry())  # type: ignore[arg-type]
        await first.storage_backend.async_save([_record()])

        second = AutocodeSearchCoordinator(hass, _entry())  # type: ignore[arg-type]
        await second.async_config_entry_first_refresh()

        assert second.success_memory.count() == 1
        assert second.success_memory.last_record() == _record()

    asyncio.run(_run())


def test_clear_success_memory_service_clears_storage_and_publishes() -> None:
    """The clear service removes persisted records and updates the coordinator."""
    hass = _hass()
    coordinator = AutocodeSearchCoordinator(hass, _entry())  # type: ignore[arg-type]
    coordinator.async_publish_session = AsyncMock()
    hass.data["autocode_search"] = {"entry-1": coordinator}

    async def _run() -> None:
        await coordinator.async_config_entry_first_refresh()
        coordinator.success_memory.load_records([_record()])
        await coordinator.storage_backend.async_save([_record()])
        await services._async_clear_success_memory(hass, SimpleNamespace())
        await _run_pending_tasks(hass)
        loaded = await coordinator.storage_backend.async_load()
        assert loaded == []

    asyncio.run(_run())

    assert coordinator.success_memory.count() == 0
    coordinator.async_publish_session.assert_awaited()
