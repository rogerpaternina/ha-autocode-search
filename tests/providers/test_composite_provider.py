"""Tests for the composite multi-provider code stream."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

from custom_components.autocode_search.models.ir_code import IRCode
from custom_components.autocode_search.models.search_filter import SearchFilter
from custom_components.autocode_search.providers.base import CodeProvider
from custom_components.autocode_search.providers.composite import (
    CompositeCodeProvider,
)
from custom_components.autocode_search.providers.factory import (
    DEFAULT_COMPOSITE_ORDER,
    ProviderFactory,
)
from custom_components.autocode_search.providers.filtering import filter_codes
from custom_components.autocode_search.providers.irdb import IRDBProvider
from custom_components.autocode_search.providers.smartir import SmartIRProvider


class FakeSmartIRProvider(CodeProvider):
    """Simulate a provider that records the filter it receives."""

    def __init__(self, codes: list[IRCode]) -> None:
        self._all_codes = codes
        self._active_codes: list[IRCode] = []
        self._index = 0
        self._loaded = False
        self.received_filter: SearchFilter | None = None
        self.reset_calls = 0

    async def load(self, search_filter: SearchFilter | None = None) -> None:
        """Load the fake codes and record the received filter."""
        self.received_filter = search_filter
        self._active_codes = filter_codes(self._all_codes, search_filter)
        self._loaded = True
        self._index = 0

    def current(self) -> IRCode | None:
        """Return the code at the cursor position."""
        if not self._loaded or not self._active_codes:
            return None
        return self._active_codes[self._index]

    def next(self) -> IRCode | None:
        """Advance the cursor and return the next code."""
        if not self._loaded or self._index >= len(self._active_codes) - 1:
            return None
        self._index += 1
        return self.current()

    def previous(self) -> IRCode | None:
        """Move the cursor back and return the previous code."""
        if not self._loaded or self._index == 0:
            return None
        self._index -= 1
        return self.current()

    def count(self) -> int:
        """Return the number of active codes."""
        return len(self._active_codes)

    def unfiltered_count(self) -> int:
        """Return the raw number of fake codes."""
        return len(self._all_codes)

    def reset(self) -> None:
        """Reset the cursor and count the invocation."""
        self.reset_calls += 1
        self._index = 0


class FakeIRDBProvider(FakeSmartIRProvider):
    """Second fake provider with a distinct display name."""


class FakeLIRCProvider(FakeSmartIRProvider):
    """Third fake provider with a distinct display name."""


def _code(name: str, payload: str, protocol: str | None = "NEC") -> IRCode:
    return IRCode(name=name, payload=payload, protocol=protocol, manufacturer="LG")


async def _collect(iterator: AsyncIterator[IRCode]) -> list[IRCode]:
    return [code async for code in iterator]


def test_single_provider_streams_all_codes() -> None:
    """One wrapped provider behaves like using it directly."""
    provider = FakeSmartIRProvider([_code("power", "p-1"), _code("mute", "p-2")])
    composite = CompositeCodeProvider([provider])

    codes = asyncio.run(_collect(composite.iter_codes()))

    assert [code.payload for code in codes] == ["p-1", "p-2"]
    assert composite.count() == 2


def test_two_providers_are_streamed_in_priority_order() -> None:
    """Codes from the first provider are delivered before the second."""
    first = FakeSmartIRProvider([_code("power", "p-1")])
    second = FakeIRDBProvider([_code("mute", "p-2")])
    composite = CompositeCodeProvider([first, second])

    codes = asyncio.run(_collect(composite.iter_codes()))

    assert [code.payload for code in codes] == ["p-1", "p-2"]


def test_three_providers_are_all_consumed() -> None:
    """Every provider in the list contributes to the stream."""
    composite = CompositeCodeProvider(
        [
            FakeSmartIRProvider([_code("power", "p-1")]),
            FakeIRDBProvider([_code("mute", "p-2")]),
            FakeLIRCProvider([_code("vol", "p-3")]),
        ]
    )

    codes = asyncio.run(_collect(composite.iter_codes()))

    assert [code.payload for code in codes] == ["p-1", "p-2", "p-3"]
    assert composite.providers_completed == ["FakeSmartIR", "FakeIRDB", "FakeLIRC"]


def test_duplicates_are_removed_by_payload_and_protocol() -> None:
    """Codes with the same payload and protocol are delivered only once."""
    first = FakeSmartIRProvider(
        [
            _code("POWER", "power-payload"),
            _code("POWER_ALT", "power-payload"),
            _code("VOL+", "vol-payload"),
        ]
    )
    second = FakeIRDBProvider(
        [
            _code("POWER", "power-payload"),
            _code("MUTE", "mute-payload"),
        ]
    )
    composite = CompositeCodeProvider([first, second])

    codes = asyncio.run(_collect(composite.iter_codes()))

    assert [code.payload for code in codes] == [
        "power-payload",
        "vol-payload",
        "mute-payload",
    ]
    assert composite.duplicates_removed == 2


def test_same_payload_different_protocol_is_not_a_duplicate() -> None:
    """Deduplication uses payload and protocol together."""
    composite = CompositeCodeProvider(
        [
            FakeSmartIRProvider([_code("power", "same", protocol="NEC")]),
            FakeIRDBProvider([_code("power", "same", protocol="RC5")]),
        ]
    )

    codes = asyncio.run(_collect(composite.iter_codes()))

    assert len(codes) == 2
    assert composite.duplicates_removed == 0


def test_search_filter_is_propagated_unchanged_to_all_providers() -> None:
    """Every wrapped provider receives the exact same filter."""
    first = FakeSmartIRProvider([_code("power", "p-1")])
    second = FakeIRDBProvider([_code("mute", "p-2")])
    composite = CompositeCodeProvider([first, second])
    search_filter = SearchFilter(manufacturer="LG", command="power")

    codes = asyncio.run(_collect(composite.iter_codes(search_filter)))

    assert first.received_filter is search_filter
    assert second.received_filter is search_filter
    assert [code.name for code in codes] == ["power"]


def test_reset_resets_composite_cursor_and_all_providers() -> None:
    """Reset restores the cursor and cascades to every provider."""
    first = FakeSmartIRProvider([_code("power", "p-1"), _code("mute", "p-2")])
    second = FakeIRDBProvider([_code("vol", "p-3")])
    composite = CompositeCodeProvider([first, second])

    async def _run() -> None:
        await composite.load()
        composite.next()
        composite.next()
        resets_before = (first.reset_calls, second.reset_calls)
        composite.reset()

        assert composite.current() is not None
        assert composite.current().payload == "p-1"
        assert first.reset_calls > resets_before[0]
        assert second.reset_calls > resets_before[1]

    asyncio.run(_run())


def test_unfiltered_count_sums_all_providers_with_duplicates() -> None:
    """The raw count adds every provider total without deduplication."""
    composite = CompositeCodeProvider(
        [
            FakeSmartIRProvider([_code("power", "same"), _code("vol", "p-2")]),
            FakeIRDBProvider([_code("power", "same")]),
        ]
    )

    asyncio.run(_collect(composite.iter_codes()))

    assert composite.unfiltered_count() == 3
    assert composite.count() == 2


def test_statistics_track_used_and_completed_providers() -> None:
    """Provider statistics reflect the executed search."""
    composite = CompositeCodeProvider(
        [
            FakeSmartIRProvider([_code("power", "p-1")]),
            FakeIRDBProvider([_code("power", "p-1"), _code("mute", "p-2")]),
        ]
    )

    asyncio.run(_collect(composite.iter_codes()))

    assert composite.providers_used == ["FakeSmartIR", "FakeIRDB"]
    assert composite.providers_completed == ["FakeSmartIR", "FakeIRDB"]
    assert composite.duplicates_removed == 1


def test_empty_providers_yield_empty_stream() -> None:
    """A composite of empty providers behaves like an empty provider."""
    composite = CompositeCodeProvider([FakeSmartIRProvider([]), FakeIRDBProvider([])])

    codes = asyncio.run(_collect(composite.iter_codes()))

    assert codes == []
    assert composite.count() == 0
    assert composite.providers_completed == ["FakeSmartIR", "FakeIRDB"]


def test_mixed_empty_and_populated_providers() -> None:
    """Empty providers do not interrupt the combined stream."""
    composite = CompositeCodeProvider(
        [
            FakeSmartIRProvider([]),
            FakeIRDBProvider([_code("power", "p-1")]),
            FakeLIRCProvider([]),
        ]
    )

    codes = asyncio.run(_collect(composite.iter_codes()))

    assert [code.payload for code in codes] == ["p-1"]
    assert composite.providers_completed == ["FakeSmartIR", "FakeIRDB", "FakeLIRC"]


class FakeConfig:
    """Resolve Home Assistant configuration paths below a temporary root."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def path(self, *parts: str) -> str:
        """Return a path relative to the fake configuration directory."""
        return str(self._root.joinpath(*parts))


class FakeHomeAssistant:
    """Expose the configuration API used by filesystem providers."""

    def __init__(self, root: Path) -> None:
        self.config = FakeConfig(root)


def test_provider_factory_creates_composite_in_configured_order(
    tmp_path: Path,
) -> None:
    """The factory builds a composite following the default provider order."""
    provider = ProviderFactory.create("composite", FakeHomeAssistant(tmp_path))

    assert isinstance(provider, CompositeCodeProvider)
    assert DEFAULT_COMPOSITE_ORDER == ("smartir", "irdb")
    inner = provider._providers
    assert isinstance(inner[0], SmartIRProvider)
    assert isinstance(inner[1], IRDBProvider)


def test_provider_factory_supports_custom_composite_order(tmp_path: Path) -> None:
    """A custom order list controls the composite priority."""
    provider = ProviderFactory.create(
        "composite",
        FakeHomeAssistant(tmp_path),
        composite_order=["irdb", "smartir"],
    )

    assert isinstance(provider, CompositeCodeProvider)
    inner = provider._providers
    assert isinstance(inner[0], IRDBProvider)
    assert isinstance(inner[1], SmartIRProvider)
