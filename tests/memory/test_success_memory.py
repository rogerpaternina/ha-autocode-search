"""Tests for success memory."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.autocode_search import services
from custom_components.autocode_search.memory import SuccessMemory
from custom_components.autocode_search.memory.success_memory import (
    normalize_provider_name,
)
from custom_components.autocode_search.models.ir_code import IRCode
from custom_components.autocode_search.models.search_filter import SearchFilter
from custom_components.autocode_search.providers.base import CodeProvider
from custom_components.autocode_search.providers.composite import CompositeCodeProvider
from custom_components.autocode_search.providers.filtering import filter_codes
from custom_components.autocode_search.providers.ranking import ProviderRanking


def _code(
    payload: str,
    *,
    manufacturer: str | None = "LG",
    model: str | None = "OLED55",
    device_type: str | None = "tv",
    name: str = "power",
) -> IRCode:
    return IRCode(
        name=name,
        payload=payload,
        protocol="NEC",
        manufacturer=manufacturer,
        model=model,
        device_type=device_type,
    )


def _filter(**kwargs: str) -> SearchFilter:
    return SearchFilter(**kwargs)


def test_remember_stores_a_success_record() -> None:
    memory = SuccessMemory()
    search_filter = _filter(manufacturer="LG", model="OLED55", command="power")

    record = memory.remember(search_filter, _code("payload-1"), "smartir")

    assert memory.count() == 1
    assert record.provider == "SmartIR"
    assert record.payload == "payload-1"
    assert record.use_count == 1


def test_remember_updates_use_count_for_duplicate_record() -> None:
    memory = SuccessMemory()
    search_filter = _filter(manufacturer="LG", model="OLED55", command="power")
    code = _code("payload-1")

    first = memory.remember(search_filter, code, "smartir")
    second = memory.remember(search_filter, code, "smartir")

    assert memory.count() == 1
    assert first.use_count == 1
    assert second.use_count == 2


def test_remember_updates_last_used_for_duplicate_record() -> None:
    memory = SuccessMemory()
    search_filter = _filter(manufacturer="LG", model="OLED55", command="power")
    code = _code("payload-1")
    first = memory.remember(search_filter, code, "smartir")
    later = datetime.now(UTC) + timedelta(minutes=5)
    second = memory.remember(search_filter, code, "smartir")

    assert second.last_used >= first.last_used
    assert second.last_used <= later


def test_find_returns_exact_manufacturer_model_command_match() -> None:
    memory = SuccessMemory()
    search_filter = _filter(manufacturer="LG", model="OLED55", command="power")
    memory.remember(search_filter, _code("payload-1"), "irdb")

    matches = memory.find(search_filter)

    assert len(matches) == 1
    assert matches[0].provider == "IRDB"


def test_find_returns_partial_manufacturer_model_match() -> None:
    memory = SuccessMemory()
    memory.remember(
        _filter(manufacturer="LG", model="OLED55", command="power"),
        _code("payload-1"),
        "irdb",
    )

    matches = memory.find(_filter(manufacturer="LG", model="OLED55"))

    assert len(matches) == 1
    assert matches[0].provider == "IRDB"


def test_find_ignores_unrelated_records() -> None:
    memory = SuccessMemory()
    memory.remember(
        _filter(manufacturer="Sony", model="RM-YD103", command="power"),
        _code("payload-1", manufacturer="Sony", model="RM-YD103"),
        "irdb",
    )

    matches = memory.find(_filter(manufacturer="LG", model="OLED55", command="power"))

    assert matches == []


def test_find_sorts_by_use_count_then_last_used() -> None:
    memory = SuccessMemory()
    older_filter = _filter(manufacturer="LG", model="OLED55", command="power")
    newer_filter = _filter(manufacturer="LG", model="OLED55", command="mute")
    memory.remember(older_filter, _code("payload-1", name="power"), "smartir")
    memory.remember(newer_filter, _code("payload-2", name="mute"), "irdb")
    memory.remember(older_filter, _code("payload-1", name="power"), "smartir")

    matches = memory.find(_filter(manufacturer="LG", model="OLED55", command="power"))

    assert [match.provider for match in matches] == ["SmartIR", "IRDB"]


def test_clear_removes_all_records() -> None:
    memory = SuccessMemory()
    memory.remember(_filter(manufacturer="LG"), _code("payload-1"), "smartir")

    memory.clear()

    assert memory.count() == 0
    assert memory.find(_filter(manufacturer="LG")) == []


def test_count_returns_number_of_records() -> None:
    memory = SuccessMemory()
    assert memory.count() == 0
    memory.remember(_filter(manufacturer="LG"), _code("payload-1"), "smartir")
    memory.remember(
        _filter(manufacturer="Sony"),
        _code("payload-2", manufacturer="Sony"),
        "irdb",
    )
    assert memory.count() == 2


def test_normalize_provider_name_maps_factory_ids() -> None:
    assert normalize_provider_name("smartir") == "SmartIR"
    assert normalize_provider_name("IRDB") == "IRDB"


class _StubProvider(CodeProvider):
    def __init__(self, codes: list[IRCode]) -> None:
        self._all_codes = codes
        self._active_codes: list[IRCode] = []
        self._index = 0
        self._loaded = False

    async def load(self, search_filter: SearchFilter | None = None) -> None:
        self._active_codes = filter_codes(self._all_codes, search_filter)
        self._loaded = True
        self._index = 0

    def current(self) -> IRCode | None:
        if not self._loaded or not self._active_codes:
            return None
        return self._active_codes[self._index]

    def next(self) -> IRCode | None:
        if not self._loaded or self._index >= len(self._active_codes) - 1:
            return None
        self._index += 1
        return self.current()

    def previous(self) -> IRCode | None:
        if not self._loaded or self._index == 0:
            return None
        self._index -= 1
        return self.current()

    def count(self) -> int:
        return len(self._active_codes)

    def unfiltered_count(self) -> int:
        return len(self._all_codes)

    def reset(self) -> None:
        self._index = 0

    async def iter_codes(
        self, search_filter: SearchFilter | None = None
    ) -> AsyncIterator[IRCode]:
        await self.load(search_filter)
        for code in self._active_codes:
            yield code


SmartIRProviderStub = type("SmartIRProvider", (_StubProvider,), {})
IRDBProviderStub = type("IRDBProvider", (_StubProvider,), {})


def test_provider_ranking_boosts_success_provider() -> None:
    memory = SuccessMemory()
    memory.remember(
        _filter(manufacturer="LG", model="OLED55", command="power"),
        _code("payload-1"),
        "smartir",
    )
    ranking = ProviderRanking(success_memory=memory)
    providers = [
        IRDBProviderStub([_code("payload-2")]),
        SmartIRProviderStub([_code("payload-1")]),
    ]

    result = ranking.rank(
        _filter(manufacturer="LG", model="OLED55", command="power"),
        providers,
    )

    assert [type(provider).__name__ for provider in result.providers] == [
        "SmartIRProvider",
        "IRDBProvider",
    ]
    assert result.reason == "Success memory (SmartIR)"


def test_provider_ranking_without_memory_keeps_existing_behavior() -> None:
    memory = SuccessMemory()
    ranking = ProviderRanking(success_memory=memory)
    providers = [
        SmartIRProviderStub([_code("payload-1")]),
        IRDBProviderStub([_code("payload-2")]),
    ]

    result = ranking.rank(
        _filter(manufacturer="Sony", model="RM-YD103"),
        providers,
    )

    assert [type(provider).__name__ for provider in result.providers] == [
        "IRDBProvider",
        "SmartIRProvider",
    ]
    assert result.reason == "Model specified"


async def _collect(iterator: AsyncIterator[IRCode]) -> list[IRCode]:
    return [code async for code in iterator]


def test_composite_uses_success_boosted_provider_order() -> None:
    memory = SuccessMemory()
    memory.remember(
        _filter(manufacturer="LG", model="OLED55", command="power"),
        _code("payload-1"),
        "smartir",
    )
    composite = CompositeCodeProvider(
        [
            IRDBProviderStub([_code("payload-2")]),
            SmartIRProviderStub([_code("payload-1")]),
        ],
        ranking=ProviderRanking(success_memory=memory),
    )
    search_filter = _filter(manufacturer="LG", model="OLED55", command="power")

    codes = asyncio.run(_collect(composite.iter_codes(search_filter)))

    assert [code.payload for code in codes] == ["payload-1", "payload-2"]
    assert composite.provider_order == ["SmartIR", "IRDB"]
    assert composite.provider_ranking_reason == "Success memory (SmartIR)"


def test_remember_logs_success_details(caplog: pytest.LogCaptureFixture) -> None:
    memory = SuccessMemory()
    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.autocode_search.memory.success_memory",
    ):
        memory.remember(
            _filter(manufacturer="LG", model="OLED55", command="power"),
            _code("payload-1"),
            "irdb",
        )

    messages = [record.message for record in caplog.records]
    assert "Success recorded" in messages
    assert "Manufacturer: LG" in messages
    assert "Model: OLED55" in messages
    assert "Command: POWER" in messages
    assert "Provider: IRDB" in messages


def test_mark_success_service_records_success() -> None:
    from types import SimpleNamespace

    from custom_components.autocode_search.coordinator import AutocodeSearchCoordinator

    entry = SimpleNamespace(
        entry_id="entry-1",
        title="Autocode Search",
        data={},
        options={},
    )
    coordinator = AutocodeSearchCoordinator(SimpleNamespace(data={}), entry)
    coordinator.async_publish_session = AsyncMock()
    coordinator.success_memory = SuccessMemory()
    hass = SimpleNamespace(data={"autocode_search": {"entry-1": coordinator}})
    call = MagicMock()
    call.data = {
        "provider": "smartir",
        "payload": "JgBQAAAB",
        "protocol": "NEC",
        "manufacturer": "LG",
        "model": "OLED55",
        "device_type": "tv",
        "command": "power",
    }

    asyncio.run(services._async_mark_success(hass, call))

    assert coordinator.success_memory.count() == 1
    record = coordinator.success_memory.last_record()
    assert record is not None
    assert record.provider == "SmartIR"
    assert record.payload == "JgBQAAAB"
    coordinator.async_publish_session.assert_awaited_once()


def test_success_sensors_read_coordinator_data() -> None:
    from types import SimpleNamespace

    from custom_components.autocode_search.coordinator import AutocodeSearchCoordinator
    from custom_components.autocode_search.sensor import (
        AutocodeLastSuccessSensor,
        AutocodeSuccessRecordsSensor,
    )

    entry = SimpleNamespace(
        entry_id="entry-1",
        title="Autocode Search",
        data={},
        options={},
    )
    coordinator = AutocodeSearchCoordinator(SimpleNamespace(data={}), entry)
    coordinator.data = {
        "success_count": 125,
        "last_success": "LG OLED55 POWER",
    }

    assert AutocodeSuccessRecordsSensor(coordinator, entry).native_value == 125
    last_success = AutocodeLastSuccessSensor(coordinator, entry).native_value
    assert last_success == "LG OLED55 POWER"
