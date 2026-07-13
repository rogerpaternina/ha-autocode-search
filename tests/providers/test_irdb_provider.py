"""Tests for the IRDB filesystem provider."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path

from custom_components.autocode_search.models.ir_code import IRCode
from custom_components.autocode_search.models.search_filter import SearchFilter
from custom_components.autocode_search.providers.factory import ProviderFactory
from custom_components.autocode_search.providers.irdb import IRDBProvider


class FakeConfig:
    """Resolve Home Assistant configuration paths below a temporary root."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def path(self, *parts: str) -> str:
        """Return a path relative to the fake configuration directory."""
        return str(self._root.joinpath(*parts))


class FakeHomeAssistant:
    """Expose the configuration API used by IRDBProvider."""

    def __init__(self, root: Path) -> None:
        self.config = FakeConfig(root)


def _provider(root: Path) -> IRDBProvider:
    return IRDBProvider(FakeHomeAssistant(root))  # type: ignore[arg-type]


def _database_path(root: Path) -> Path:
    return root / "irdb" / "codes"


def _write_csv_file(
    root: Path,
    manufacturer: str,
    device_type: str,
    filename: str,
    rows: list[tuple[str, str, str, str, str]],
) -> Path:
    database_path = _database_path(root) / manufacturer / device_type
    database_path.mkdir(parents=True, exist_ok=True)
    csv_file = database_path / filename
    csv_file.write_text(
        "functionname,protocol,device,subdevice,function\n"
        + "\n".join(
            f"{function_name},{protocol},{device},{subdevice},{function}"
            for function_name, protocol, device, subdevice, function in rows
        ),
        encoding="utf-8",
    )
    return csv_file


def _write_json_file(
    root: Path,
    manufacturer: str,
    device_type: str,
    filename: str,
    payload: dict[str, object],
) -> Path:
    database_path = _database_path(root) / manufacturer / device_type
    database_path.mkdir(parents=True, exist_ok=True)
    json_file = database_path / filename
    json_file.write_text(json.dumps(payload), encoding="utf-8")
    return json_file


async def _collect(iterator: AsyncIterator[IRCode]) -> list[IRCode]:
    return [code async for code in iterator]


def test_missing_database_returns_no_codes(tmp_path: Path, caplog) -> None:
    """A missing IRDB installation behaves like an empty provider."""
    with caplog.at_level(logging.WARNING):
        provider = _provider(tmp_path)
        codes = asyncio.run(_collect(provider.iter_codes()))

    assert codes == []
    assert provider.count() == 0
    assert provider.unfiltered_count() == 0
    assert "IRDB database not found" in caplog.text


def test_empty_database_returns_no_codes(tmp_path: Path) -> None:
    """An installed but empty IRDB database yields no codes."""
    _database_path(tmp_path).mkdir(parents=True)
    provider = _provider(tmp_path)

    assert asyncio.run(_collect(provider.iter_codes())) == []


def test_csv_file_is_converted_to_ir_code(tmp_path: Path) -> None:
    """IRDB CSV metadata and rows are normalized into IRCode."""
    _write_csv_file(
        tmp_path,
        "Sony",
        "TV",
        "RM-YD103.csv",
        [
            ("POWER", "RC5", "20", "0", "12"),
            ("VOLUME_UP", "RC5", "20", "0", "16"),
        ],
    )

    codes = asyncio.run(_collect(_provider(tmp_path).iter_codes()))

    assert codes == [
        IRCode(
            name="POWER",
            payload="RC5:20,0,12",
            protocol="RC5",
            manufacturer="Sony",
            model="RM-YD103",
            device_type="TV",
            supported_models=("RM-YD103",),
        ),
        IRCode(
            name="VOLUME_UP",
            payload="RC5:20,0,16",
            protocol="RC5",
            manufacturer="Sony",
            model="RM-YD103",
            device_type="TV",
            supported_models=("RM-YD103",),
        ),
    ]


def test_multiple_files_are_discovered(tmp_path: Path) -> None:
    """Every supported IRDB file below the database root is loaded."""
    _write_csv_file(
        tmp_path,
        "Sony",
        "TV",
        "RM-YD103.csv",
        [("POWER", "RC5", "20", "0", "12")],
    )
    _write_csv_file(
        tmp_path,
        "LG",
        "TV",
        "OLED55.csv",
        [("power", "NEC", "7", "7", "2")],
    )
    provider = _provider(tmp_path)

    codes = asyncio.run(_collect(provider.iter_codes()))

    assert {code.manufacturer for code in codes} == {"Sony", "LG"}
    assert provider.unfiltered_count() == 2


def test_json_files_are_supported(tmp_path: Path) -> None:
    """IRDB JSON files are converted using the shared command structure."""
    _write_json_file(
        tmp_path,
        "Sony",
        "tv",
        "remote.json",
        {
            "manufacturer": "Sony",
            "device_type": "tv",
            "supportedModels": ["RM-YD103"],
            "protocol": "RC5",
            "commands": {"power": "json-power", "volume_up": "json-volume"},
        },
    )

    codes = asyncio.run(_collect(_provider(tmp_path).iter_codes()))

    assert [(code.name, code.payload) for code in codes] == [
        ("power", "json-power"),
        ("volume_up", "json-volume"),
    ]


def test_filter_by_manufacturer_is_case_insensitive(tmp_path: Path) -> None:
    """Manufacturer filters return only matching IRDB codes."""
    _write_csv_file(
        tmp_path,
        "LG",
        "TV",
        "oled.csv",
        [("power", "NEC", "7", "7", "2")],
    )
    _write_csv_file(
        tmp_path,
        "Samsung",
        "TV",
        "qled.csv",
        [("power", "NEC", "8", "8", "2")],
    )
    search_filter = SearchFilter(manufacturer=" lg ")
    provider = _provider(tmp_path)

    codes = asyncio.run(_collect(provider.iter_codes(search_filter)))

    assert [code.payload for code in codes] == ["NEC:7,7,2"]
    assert provider.unfiltered_count() == 2


def test_filter_by_model_device_type_and_command(tmp_path: Path) -> None:
    """Combined filters narrow IRDB results to exact matches."""
    _write_csv_file(
        tmp_path,
        "Sony",
        "tv",
        "RM-YD103.csv",
        [
            ("power", "RC5", "20", "0", "12"),
            ("volume_up", "RC5", "20", "0", "16"),
        ],
    )
    _write_csv_file(
        tmp_path,
        "Sony",
        "fan",
        "RM-FAN.csv",
        [("power", "RC5", "21", "0", "12")],
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
    assert codes[0].device_type == "tv"


def test_filter_without_results_returns_empty_provider(tmp_path: Path) -> None:
    """A filter with no matches yields an empty active search."""
    _write_csv_file(
        tmp_path,
        "Sony",
        "TV",
        "RM-YD103.csv",
        [("power", "RC5", "20", "0", "12")],
    )
    provider = _provider(tmp_path)

    codes = asyncio.run(_collect(provider.iter_codes(SearchFilter(manufacturer="LG"))))

    assert codes == []
    assert provider.count() == 0
    assert provider.unfiltered_count() == 1


def test_cache_avoids_reloading_changed_files(tmp_path: Path) -> None:
    """Subsequent loads reuse the first filesystem snapshot."""
    csv_file = _write_csv_file(
        tmp_path,
        "Sony",
        "TV",
        "RM-YD103.csv",
        [("power", "RC5", "20", "0", "12")],
    )
    provider = _provider(tmp_path)
    first = asyncio.run(_collect(provider.iter_codes()))
    csv_file.write_text("invalid", encoding="utf-8")

    second = asyncio.run(_collect(provider.iter_codes()))

    assert second == first
    assert provider.unfiltered_count() == 1


def test_clear_cache_reloads_database(tmp_path: Path) -> None:
    """Clearing the cache forces the provider to read the database again."""
    csv_file = _write_csv_file(
        tmp_path,
        "Sony",
        "TV",
        "RM-YD103.csv",
        [("power", "RC5", "20", "0", "12")],
    )
    provider = _provider(tmp_path)
    asyncio.run(_collect(provider.iter_codes()))
    csv_file.write_text("invalid", encoding="utf-8")
    provider.clear_cache()

    codes = asyncio.run(_collect(provider.iter_codes()))

    assert codes == []


def test_reset_restores_cursor(tmp_path: Path) -> None:
    """Reset returns the provider cursor to the first filtered code."""
    _write_csv_file(
        tmp_path,
        "Sony",
        "TV",
        "RM-YD103.csv",
        [
            ("power", "RC5", "20", "0", "12"),
            ("volume_up", "RC5", "20", "0", "16"),
        ],
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


def test_provider_factory_creates_irdb_provider(tmp_path: Path) -> None:
    """ProviderFactory can create an IRDB provider bound to Home Assistant."""
    provider = ProviderFactory.create("irdb", FakeHomeAssistant(tmp_path))

    assert isinstance(provider, IRDBProvider)
    assert asyncio.run(_collect(provider.iter_codes())) == []
