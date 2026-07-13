"""Tests for the Home Assistant storage backend."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from custom_components.autocode_search.memory.models import SuccessRecord
from custom_components.autocode_search.memory.success_memory import SuccessMemory
from custom_components.autocode_search.storage.storage_backend import StorageBackend


def _record(provider: str = "SmartIR", use_count: int = 1) -> SuccessRecord:
    return SuccessRecord(
        manufacturer="LG",
        model="OLED55",
        device_type="tv",
        command="power",
        provider=provider,
        protocol="NEC",
        payload="JgBQAAAB",
        last_used=datetime(2026, 7, 13, 12, 0, tzinfo=UTC),
        use_count=use_count,
    )


def _hass() -> SimpleNamespace:
    tasks: list[object] = []

    def async_create_task(coro: object) -> object:
        tasks.append(coro)
        return coro

    hass = SimpleNamespace(async_create_task=async_create_task)
    hass._tasks = tasks
    return hass


async def _run_pending_tasks(hass: SimpleNamespace) -> None:
    while hass._tasks:
        task = hass._tasks.pop(0)
        await task


def test_async_load_returns_empty_list_for_empty_storage() -> None:
    """An empty storage file loads as an empty record list."""
    backend = StorageBackend(_hass())

    records = asyncio.run(backend.async_load())

    assert records == []


def test_async_save_and_load_round_trip() -> None:
    """Saved records are restored on the next load."""
    hass = _hass()
    backend = StorageBackend(hass)
    records = [_record(), _record(provider="IRDB", use_count=2)]

    async def _run() -> list[SuccessRecord]:
        await backend.async_save(records)
        return await backend.async_load()

    loaded = asyncio.run(_run())

    assert loaded == records


def test_attach_persists_remembered_records() -> None:
    """Remembering a success schedules a storage save."""
    hass = _hass()
    backend = StorageBackend(hass)
    memory = SuccessMemory()
    backend.attach(memory)

    from custom_components.autocode_search.models.ir_code import IRCode
    from custom_components.autocode_search.models.search_filter import SearchFilter

    memory.remember(
        SearchFilter(manufacturer="LG", model="OLED55", command="power"),
        IRCode(
            name="power",
            payload="JgBQAAAB",
            protocol="NEC",
            manufacturer="LG",
            model="OLED55",
        ),
        "smartir",
    )

    asyncio.run(_run_pending_tasks(hass))
    loaded = asyncio.run(backend.async_load())

    assert len(loaded) == 1
    assert loaded[0].provider == "SmartIR"


def test_clear_persists_empty_storage(caplog: pytest.LogCaptureFixture) -> None:
    """Clearing memory also clears the persisted storage payload."""
    hass = _hass()
    backend = StorageBackend(hass)
    memory = SuccessMemory()
    backend.attach(memory)

    async def _run() -> list[SuccessRecord]:
        await backend.async_save([_record()])
        memory.clear()
        await _run_pending_tasks(hass)
        return await backend.async_load()

    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.autocode_search.storage.storage_backend",
    ):
        loaded = asyncio.run(_run())

    assert loaded == []
    assert "Storage cleared" in [record.message for record in caplog.records]


def test_load_logs_record_count(caplog: pytest.LogCaptureFixture) -> None:
    """Loading storage emits debug logs with the record count."""
    hass = _hass()
    backend = StorageBackend(hass)

    async def _run() -> None:
        await backend.async_save([_record(), _record(provider="IRDB")])
        await backend.async_load()

    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.autocode_search.storage.storage_backend",
    ):
        asyncio.run(_run())

    messages = [record.message for record in caplog.records]
    assert "Loading Success Memory" in messages
    assert "Loaded 2 records" in messages
