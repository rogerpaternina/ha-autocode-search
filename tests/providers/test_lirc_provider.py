"""Tests for the LIRC filesystem provider."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from pathlib import Path

from custom_components.autocode_search.models.ir_code import IRCode
from custom_components.autocode_search.models.search_filter import SearchFilter
from custom_components.autocode_search.providers.composite import CompositeCodeProvider
from custom_components.autocode_search.providers.factory import ProviderFactory
from custom_components.autocode_search.providers.lirc import LIRCProvider
from custom_components.autocode_search.providers.lirc_reader import parse_lirc_config
from custom_components.autocode_search.providers.memory import InMemoryCodeProvider


class FakeConfig:
    """Resolve Home Assistant configuration paths below a temporary root."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def path(self, *parts: str) -> str:
        """Return a path relative to the fake configuration directory."""
        return str(self._root.joinpath(*parts))


class FakeHomeAssistant:
    """Expose the configuration API used by LIRCProvider."""

    def __init__(self, root: Path) -> None:
        self.config = FakeConfig(root)


def _provider(root: Path) -> LIRCProvider:
    return LIRCProvider(FakeHomeAssistant(root))  # type: ignore[arg-type]


def _remotes_path(root: Path) -> Path:
    return root / "lirc" / "remotes"


def _write_conf_file(
    root: Path,
    manufacturer: str,
    device_type: str,
    filename: str,
    content: str,
) -> Path:
    database_path = _remotes_path(root) / manufacturer / device_type
    database_path.mkdir(parents=True, exist_ok=True)
    conf_file = database_path / filename
    conf_file.write_text(content, encoding="utf-8")
    return conf_file


def _sony_remote_conf() -> str:
    return """
begin remote
  name  Sony_RM-YD103
  protocol RC5
  begin codes
    KEY_POWER  0x000000000000A90
    KEY_MUTE   0x000000000000290
  end codes
end remote
"""


async def _collect(iterator: AsyncIterator[IRCode]) -> list[IRCode]:
    return [code async for code in iterator]


def test_missing_database_returns_no_codes(tmp_path: Path, caplog) -> None:
    """A missing LIRC installation behaves like an empty provider."""
    with caplog.at_level(logging.WARNING):
        provider = _provider(tmp_path)
        codes = asyncio.run(_collect(provider.iter_codes()))

    assert codes == []
    assert provider.count() == 0
    assert provider.unfiltered_count() == 0
    assert "LIRC database not found" in caplog.text


def test_empty_database_returns_no_codes(tmp_path: Path) -> None:
    """An installed but empty LIRC database yields no codes."""
    _remotes_path(tmp_path).mkdir(parents=True)
    provider = _provider(tmp_path)

    assert asyncio.run(_collect(provider.iter_codes())) == []


def test_parser_extracts_remote_commands() -> None:
    """The LIRC parser extracts protocol, command, and payload values."""
    remotes = parse_lirc_config(_sony_remote_conf())

    assert len(remotes) == 1
    remote = remotes[0]
    assert remote.name == "Sony_RM-YD103"
    assert remote.protocol == "RC5"
    assert remote.commands == (
        ("KEY_POWER", "0x000000000000A90"),
        ("KEY_MUTE", "0x000000000000290"),
    )


def test_conf_file_is_converted_to_ir_code(tmp_path: Path) -> None:
    """LIRC configuration metadata and commands are normalized into IRCode."""
    _write_conf_file(
        tmp_path,
        "Sony",
        "tv",
        "RM-YD103.conf",
        _sony_remote_conf(),
    )

    codes = asyncio.run(_collect(_provider(tmp_path).iter_codes()))

    assert codes == [
        IRCode(
            name="power",
            payload="0x000000000000A90",
            protocol="RC5",
            manufacturer="Sony",
            model="RM-YD103",
            device_type="tv",
            supported_models=("RM-YD103",),
        ),
        IRCode(
            name="mute",
            payload="0x000000000000290",
            protocol="RC5",
            manufacturer="Sony",
            model="RM-YD103",
            device_type="tv",
            supported_models=("RM-YD103",),
        ),
    ]


def test_lircd_conf_extension_is_supported(tmp_path: Path) -> None:
    """Files ending with .lircd.conf are discovered and parsed."""
    _write_conf_file(
        tmp_path,
        "LG",
        "tv",
        "oled55.lircd.conf",
        _sony_remote_conf().replace("Sony_RM-YD103", "LG_OLED55"),
    )

    codes = asyncio.run(_collect(_provider(tmp_path).iter_codes()))

    assert len(codes) == 2
    assert codes[0].manufacturer == "LG"
    assert codes[0].model == "oled55"


def test_multiple_files_are_discovered(tmp_path: Path) -> None:
    """Every supported LIRC file below the database root is loaded."""
    _write_conf_file(
        tmp_path,
        "Sony",
        "tv",
        "RM-YD103.conf",
        _sony_remote_conf(),
    )
    _write_conf_file(
        tmp_path,
        "LG",
        "tv",
        "OLED55.conf",
        _sony_remote_conf().replace("Sony_RM-YD103", "LG_OLED55"),
    )
    provider = _provider(tmp_path)

    codes = asyncio.run(_collect(provider.iter_codes()))

    assert {code.manufacturer for code in codes} == {"Sony", "LG"}
    assert provider.unfiltered_count() == 4


def test_filter_by_manufacturer_model_and_command(tmp_path: Path) -> None:
    """Combined filters narrow LIRC results to exact matches."""
    _write_conf_file(
        tmp_path,
        "Sony",
        "tv",
        "RM-YD103.conf",
        _sony_remote_conf(),
    )
    search_filter = SearchFilter(
        manufacturer="Sony",
        device_type="tv",
        command="power",
        model="rm-yd103",
    )
    provider = _provider(tmp_path)

    codes = asyncio.run(_collect(provider.iter_codes(search_filter)))

    assert len(codes) == 1
    assert codes[0].name == "power"
    assert codes[0].protocol == "RC5"


def test_filter_without_results_returns_empty_provider(tmp_path: Path) -> None:
    """A filter with no matches yields an empty active search."""
    _write_conf_file(
        tmp_path,
        "Sony",
        "tv",
        "RM-YD103.conf",
        _sony_remote_conf(),
    )
    provider = _provider(tmp_path)

    codes = asyncio.run(_collect(provider.iter_codes(SearchFilter(manufacturer="LG"))))

    assert codes == []
    assert provider.count() == 0
    assert provider.unfiltered_count() == 2


def test_cache_avoids_reloading_changed_files(tmp_path: Path) -> None:
    """Subsequent loads reuse the first filesystem snapshot."""
    conf_file = _write_conf_file(
        tmp_path,
        "Sony",
        "tv",
        "RM-YD103.conf",
        _sony_remote_conf(),
    )
    provider = _provider(tmp_path)
    first = asyncio.run(_collect(provider.iter_codes()))
    conf_file.write_text("invalid", encoding="utf-8")

    second = asyncio.run(_collect(provider.iter_codes()))

    assert second == first
    assert provider.unfiltered_count() == 2


def test_clear_cache_reloads_database(tmp_path: Path) -> None:
    """Clearing the cache forces the provider to read the database again."""
    conf_file = _write_conf_file(
        tmp_path,
        "Sony",
        "tv",
        "RM-YD103.conf",
        _sony_remote_conf(),
    )
    provider = _provider(tmp_path)
    asyncio.run(_collect(provider.iter_codes()))
    conf_file.write_text("invalid", encoding="utf-8")
    provider.clear_cache()

    codes = asyncio.run(_collect(provider.iter_codes()))

    assert codes == []


def test_reset_restores_cursor(tmp_path: Path) -> None:
    """Reset returns the provider cursor to the first filtered code."""
    _write_conf_file(
        tmp_path,
        "Sony",
        "tv",
        "RM-YD103.conf",
        _sony_remote_conf(),
    )
    provider = _provider(tmp_path)

    async def _run() -> None:
        await provider.load()
        assert provider.current() is not None
        provider.next()
        provider.reset()

        assert provider.current() is not None
        assert provider.current().name == "power"

    asyncio.run(_run())


def test_provider_factory_creates_lirc_provider(tmp_path: Path) -> None:
    """ProviderFactory can create a LIRC provider bound to Home Assistant."""
    provider = ProviderFactory.create("lirc", FakeHomeAssistant(tmp_path))

    assert isinstance(provider, LIRCProvider)
    assert asyncio.run(_collect(provider.iter_codes())) == []


def test_composite_provider_includes_lirc_codes(tmp_path: Path) -> None:
    """CompositeProvider streams LIRC codes together with other providers."""
    _write_conf_file(
        tmp_path,
        "Sony",
        "tv",
        "RM-YD103.conf",
        _sony_remote_conf(),
    )
    composite = CompositeCodeProvider(
        [
            InMemoryCodeProvider(
                [
                    IRCode(
                        name="power",
                        payload="memory-payload",
                        manufacturer="Sony",
                    )
                ]
            ),
            _provider(tmp_path),
        ]
    )
    search_filter = SearchFilter(manufacturer="Sony", command="power")

    codes = asyncio.run(_collect(composite.iter_codes(search_filter)))

    assert [code.payload for code in codes] == [
        "memory-payload",
        "0x000000000000A90",
    ]
