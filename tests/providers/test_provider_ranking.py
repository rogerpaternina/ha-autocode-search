"""Tests for smart provider ranking."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

import pytest

from custom_components.autocode_search.models.ir_code import IRCode
from custom_components.autocode_search.models.search_filter import SearchFilter
from custom_components.autocode_search.providers.base import CodeProvider
from custom_components.autocode_search.providers.composite import (
    CompositeCodeProvider,
)
from custom_components.autocode_search.providers.filtering import filter_codes
from custom_components.autocode_search.providers.ranking import (
    ProviderRanking,
    RankingResult,
    provider_display_name,
)


class _StubProvider(CodeProvider):
    """Minimal provider stub for ranking tests."""

    def __init__(self, codes: list[IRCode] | None = None) -> None:
        self._all_codes = codes or []
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
LIRCProviderStub = type("LIRCProvider", (_StubProvider,), {})
UnknownProviderStub = type("UnknownProvider", (_StubProvider,), {})


def _code(name: str, payload: str) -> IRCode:
    return IRCode(name=name, payload=payload, protocol="NEC", manufacturer="LG")


def _providers() -> list[CodeProvider]:
    return [
        SmartIRProviderStub([_code("power", "p-1")]),
        IRDBProviderStub([_code("mute", "p-2")]),
    ]


def _rank(
    search_filter: SearchFilter | None,
    providers: list[CodeProvider] | None = None,
) -> RankingResult:
    return ProviderRanking().rank(search_filter, providers or _providers())


def _names(result: RankingResult) -> list[str]:
    return [provider_display_name(provider) for provider in result.providers]


def test_no_filter_keeps_default_order() -> None:
    """Without an active filter the default SmartIR-first order is used."""
    result = _rank(None)

    assert _names(result) == ["SmartIR", "IRDB"]
    assert result.reason == "Default order"


def test_inactive_filter_keeps_default_order() -> None:
    """A filter with no criteria keeps the configured provider order."""
    result = _rank(SearchFilter())

    assert _names(result) == ["SmartIR", "IRDB"]
    assert result.reason == "Default order"


def test_manufacturer_only_prioritizes_smartir() -> None:
    """Manufacturer-only searches prefer SmartIR."""
    result = _rank(SearchFilter(manufacturer="LG"))

    assert _names(result) == ["SmartIR", "IRDB"]
    assert result.reason == "Default order"


def test_model_only_prioritizes_irdb() -> None:
    """Model-only searches prefer IRDB."""
    result = _rank(SearchFilter(model="RM-YD103"))

    assert _names(result) == ["IRDB", "SmartIR"]
    assert result.reason == "Model specified"


def test_manufacturer_and_model_prioritizes_irdb() -> None:
    """Manufacturer and model together prefer IRDB."""
    result = _rank(SearchFilter(manufacturer="Sony", model="RM-YD103"))

    assert _names(result) == ["IRDB", "SmartIR"]
    assert result.reason == "Model specified"


def test_climate_device_prioritizes_smartir() -> None:
    """Climate device searches prefer SmartIR."""
    result = _rank(SearchFilter(device_type="climate"))

    assert _names(result) == ["SmartIR", "IRDB"]
    assert result.reason == "Climate device"


def test_climate_with_manufacturer_prioritizes_smartir() -> None:
    """Climate plus manufacturer still prefers SmartIR."""
    result = _rank(SearchFilter(manufacturer="LG", device_type="climate"))

    assert _names(result) == ["SmartIR", "IRDB"]
    assert result.reason == "Climate device"


def test_unknown_provider_is_preserved_after_known_providers() -> None:
    """Unknown providers remain after ranked known providers."""
    providers = [
        UnknownProviderStub([_code("custom", "p-0")]),
        SmartIRProviderStub([_code("power", "p-1")]),
        IRDBProviderStub([_code("mute", "p-2")]),
    ]
    result = _rank(SearchFilter(model="RM-YD103"), providers)

    assert _names(result) == ["IRDB", "SmartIR", "Unknown"]


def test_single_provider_is_returned_unchanged() -> None:
    """Ranking a single provider does not alter the list."""
    providers = [SmartIRProviderStub([_code("power", "p-1")])]
    result = _rank(SearchFilter(model="RM-YD103"), providers)

    assert _names(result) == ["SmartIR"]
    assert result.reason == "Model specified"


def test_three_providers_are_all_returned_in_ranked_order() -> None:
    """Three providers are all included in the ranked result."""
    providers = [
        SmartIRProviderStub([_code("power", "p-1")]),
        IRDBProviderStub([_code("mute", "p-2")]),
        LIRCProviderStub([_code("vol", "p-3")]),
    ]
    result = _rank(SearchFilter(model="RM-YD103"), providers)

    assert _names(result) == ["IRDB", "SmartIR", "LIRC"]
    assert result.reason == "Model specified"


def test_ranking_result_dataclass() -> None:
    """RankingResult exposes providers and the ranking reason."""
    providers = _providers()
    result = RankingResult(providers, "Model specified")

    assert result.providers == providers
    assert result.reason == "Model specified"


async def _collect(iterator: AsyncIterator[IRCode]) -> list[IRCode]:
    return [code async for code in iterator]


def test_composite_integration_uses_ranked_order_for_model_filter() -> None:
    """CompositeProvider consults providers in the ranked order."""
    smartir = SmartIRProviderStub(
        [
            IRCode(
                name="power",
                payload="p-1",
                protocol="NEC",
                manufacturer="Sony",
                model="RM-YD103",
            )
        ]
    )
    irdb = IRDBProviderStub(
        [
            IRCode(
                name="mute",
                payload="p-2",
                protocol="NEC",
                manufacturer="Sony",
                model="RM-YD103",
            )
        ]
    )
    composite = CompositeCodeProvider([smartir, irdb])
    search_filter = SearchFilter(manufacturer="Sony", model="RM-YD103")

    codes = asyncio.run(_collect(composite.iter_codes(search_filter)))

    assert [code.payload for code in codes] == ["p-2", "p-1"]
    assert composite.provider_order == ["IRDB", "SmartIR"]
    assert composite.provider_ranking_reason == "Model specified"
    assert composite.providers_used == ["IRDB", "SmartIR"]


def test_composite_integration_keeps_default_order_without_filter() -> None:
    """CompositeProvider keeps the configured order when no filter is active."""
    composite = CompositeCodeProvider(
        [
            SmartIRProviderStub([_code("power", "p-1")]),
            IRDBProviderStub([_code("mute", "p-2")]),
        ]
    )

    codes = asyncio.run(_collect(composite.iter_codes()))

    assert [code.payload for code in codes] == ["p-1", "p-2"]
    assert composite.provider_order == ["SmartIR", "IRDB"]
    assert composite.provider_ranking_reason == "Default order"


def test_ranking_logs_filter_and_result(caplog: pytest.LogCaptureFixture) -> None:
    """Ranking emits debug logs for the filter and resulting order."""
    with caplog.at_level(
        logging.DEBUG,
        logger="custom_components.autocode_search.providers.ranking",
    ):
        _rank(SearchFilter(manufacturer="Sony", model="RM-YD103"))

    messages = [record.message for record in caplog.records]
    assert "Provider ranking started" in messages
    assert "manufacturer=Sony" in messages
    assert "model=RM-YD103" in messages
    assert "Ranking result" in messages
    assert "IRDB" in messages
    assert "SmartIR" in messages
    assert "Reason:" in messages
    assert "Model specified" in messages
