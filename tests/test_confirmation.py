"""Tests for the user confirmation workflow."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.autocode_search import services
from custom_components.autocode_search.binary_sensor import (
    AutocodeWaitingConfirmationBinarySensor,
)
from custom_components.autocode_search.button import (
    AutocodeConfirmSuccessButton,
    AutocodeRejectResultButton,
)
from custom_components.autocode_search.coordinator import AutocodeSearchCoordinator
from custom_components.autocode_search.memory import SuccessMemory
from custom_components.autocode_search.models.ir_code import IRCode
from custom_components.autocode_search.models.search_filter import SearchFilter
from custom_components.autocode_search.models.search_session import (
    SearchSession,
    SearchStatus,
)
from custom_components.autocode_search.sensor import (
    AutocodeLastProviderSensor,
    AutocodeLastTestedCommandSensor,
)
from tests.test_search_engine import FakeAdapter, FakeProvider


def _entry() -> SimpleNamespace:
    return SimpleNamespace(
        entry_id="entry-1",
        title="Autocode Search",
        data={},
        options={},
    )


def _hass(coordinator: AutocodeSearchCoordinator) -> SimpleNamespace:
    hass = SimpleNamespace(data={"autocode_search": {"entry-1": coordinator}})
    hass.services = SimpleNamespace(async_call=AsyncMock())
    return hass


def _code() -> IRCode:
    return IRCode(
        name="power",
        payload="payload-1",
        protocol="NEC",
        manufacturer="LG",
        model="OLED55",
        device_type="tv",
    )


def _session() -> SearchSession:
    now = datetime.now(UTC)
    return SearchSession(
        session_id="session-1",
        device_type="tv",
        brand="lg",
        command="power",
        current_index=1,
        total_codes=2,
        codes_after_filter=2,
        codes_tested=1,
        status=SearchStatus.RUNNING,
        started_at=now,
        last_update=now,
    )


def _create_coordinator() -> AutocodeSearchCoordinator:
    hass = SimpleNamespace(data={}, async_create_task=lambda coro: coro)
    coordinator = AutocodeSearchCoordinator(hass, _entry())  # type: ignore[arg-type]
    coordinator.async_set_updated_data = MagicMock()
    coordinator.async_publish_session = AsyncMock()
    coordinator.success_memory = SuccessMemory()
    return coordinator


def test_search_session_confirmation_state_helpers() -> None:
    """SearchSession tracks confirmation metadata independently."""
    session = _session()
    code = _code()

    session.capture_last_tested(code, "SmartIR")
    session.activate_confirmation()

    assert session.last_tested_code == code
    assert session.last_provider == "SmartIR"
    assert session.awaiting_confirmation is True
    assert session.confirmation_time is not None

    session.clear_confirmation()

    assert session.awaiting_confirmation is False
    assert session.confirmation_time is None
    assert session.last_tested_code == code

    session.reset_confirmation_state()

    assert session.last_tested_code is None
    assert session.last_provider is None


def test_finish_search_prepares_confirmation() -> None:
    """Finishing a search exposes the last tested code for confirmation."""
    coordinator = _create_coordinator()
    provider = FakeProvider([_code()])
    adapter = FakeAdapter()
    session = _session()
    search_filter = SearchFilter(manufacturer="LG", model="OLED55", command="power")

    async def _run() -> None:
        engine = await coordinator.async_start_search(
            provider, adapter, session, search_filter
        )
        await engine.send_current()
        await coordinator.async_finish_search()

    asyncio.run(_run())

    assert coordinator.search_session.status is SearchStatus.FINISHED
    assert coordinator.search_session.awaiting_confirmation is True
    assert coordinator.search_session.last_provider == "Fake"
    assert coordinator.search_session.last_tested_code == _code()


def test_confirm_success_remembers_last_tested_code() -> None:
    """Confirming a result stores the last tested code in success memory."""
    coordinator = _create_coordinator()
    provider = FakeProvider([_code()])
    adapter = FakeAdapter()
    session = _session()
    search_filter = SearchFilter(manufacturer="LG", model="OLED55", command="power")

    async def _run() -> None:
        engine = await coordinator.async_start_search(
            provider, adapter, session, search_filter
        )
        await engine.send_current()
        await coordinator.async_finish_search()
        await coordinator.async_confirm_success()

    asyncio.run(_run())

    assert coordinator.success_memory.count() == 1
    assert coordinator.search_session.awaiting_confirmation is False
    record = coordinator.success_memory.last_record()
    assert record is not None
    assert record.provider == "Fake"
    assert record.payload == "payload-1"


def test_reject_result_clears_confirmation_without_remembering() -> None:
    """Rejecting a result dismisses confirmation without learning."""
    coordinator = _create_coordinator()
    provider = FakeProvider([_code()])
    adapter = FakeAdapter()
    session = _session()

    async def _run() -> None:
        engine = await coordinator.async_start_search(provider, adapter, session)
        await engine.send_current()
        await coordinator.async_finish_search()
        await coordinator.async_reject_result()

    asyncio.run(_run())

    assert coordinator.success_memory.count() == 0
    assert coordinator.search_session.awaiting_confirmation is False


def test_confirm_success_service_delegates_to_coordinator() -> None:
    """The confirm_success service delegates to the coordinator."""
    coordinator = _create_coordinator()
    coordinator.async_confirm_success = AsyncMock()
    hass = _hass(coordinator)

    asyncio.run(services._async_confirm_success(hass, MagicMock()))

    coordinator.async_confirm_success.assert_awaited_once()


def test_reject_result_service_delegates_to_coordinator() -> None:
    """The reject_result service delegates to the coordinator."""
    coordinator = _create_coordinator()
    coordinator.async_reject_result = AsyncMock()
    hass = _hass(coordinator)

    asyncio.run(services._async_reject_result(hass, MagicMock()))

    coordinator.async_reject_result.assert_awaited_once()


def test_mark_success_remains_compatible() -> None:
    """The legacy mark_success service still records successes manually."""
    coordinator = _create_coordinator()
    hass = _hass(coordinator)
    call = MagicMock()
    call.data = {
        "provider": "smartir",
        "payload": "JgBQAAAB",
        "protocol": "NEC",
        "manufacturer": "LG",
        "model": "OLED55",
        "command": "power",
    }

    asyncio.run(services._async_mark_success(hass, call))

    assert coordinator.success_memory.count() == 1
    coordinator.async_publish_session.assert_awaited()


def test_waiting_confirmation_binary_sensor_reflects_coordinator_data() -> None:
    """The waiting-confirmation binary sensor follows coordinator state."""
    coordinator = _create_coordinator()
    coordinator.data = {"awaiting_confirmation": True}
    sensor = AutocodeWaitingConfirmationBinarySensor(coordinator, _entry())  # type: ignore[arg-type]

    assert sensor.is_on is True


def test_last_provider_and_command_sensors_reflect_coordinator_data() -> None:
    """New sensors expose the last tested provider and command."""
    coordinator = _create_coordinator()
    coordinator.data = {
        "last_provider": "SmartIR",
        "last_tested_command": "POWER",
    }
    entry = _entry()

    assert AutocodeLastProviderSensor(coordinator, entry).native_value == "SmartIR"  # type: ignore[arg-type]
    assert (
        AutocodeLastTestedCommandSensor(coordinator, entry).native_value == "POWER"
    )  # type: ignore[arg-type]


def test_confirm_button_invokes_service() -> None:
    """The confirm button invokes the confirm_success service."""
    coordinator = _create_coordinator()
    hass = _hass(coordinator)
    coordinator.hass = hass
    button = AutocodeConfirmSuccessButton(coordinator, _entry())  # type: ignore[arg-type]

    asyncio.run(button.async_press())

    hass.services.async_call.assert_awaited_once_with(
        "autocode_search",
        "confirm_success",
        {},
        blocking=True,
    )


def test_reject_button_invokes_service() -> None:
    """The reject button invokes the reject_result service."""
    coordinator = _create_coordinator()
    hass = _hass(coordinator)
    coordinator.hass = hass
    button = AutocodeRejectResultButton(coordinator, _entry())  # type: ignore[arg-type]

    asyncio.run(button.async_press())

    hass.services.async_call.assert_awaited_once_with(
        "autocode_search",
        "reject_result",
        {},
        blocking=True,
    )


def test_confirm_success_logs_debug_messages(caplog: pytest.LogCaptureFixture) -> None:
    """Confirming a result emits the expected debug logs."""
    coordinator = _create_coordinator()
    provider = FakeProvider([_code()])
    adapter = FakeAdapter()
    session = _session()

    async def _run() -> None:
        engine = await coordinator.async_start_search(provider, adapter, session)
        await engine.send_current()
        await coordinator.async_finish_search()
        with caplog.at_level(
            logging.DEBUG,
            logger="custom_components.autocode_search.success_workflow",
        ):
            await coordinator.async_confirm_success()

    asyncio.run(_run())

    messages = [record.message for record in caplog.records]
    assert "User confirmed successful code" in messages
    assert "Success stored" in messages
    assert "Persistence completed" in messages
