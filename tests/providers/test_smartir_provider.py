"""Tests for the SmartIR filesystem provider."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from custom_components.autocode_search.models.ir_code import IRCode
from custom_components.autocode_search.providers.smartir import SmartIRProvider


class FakeConfig:
    """Resolve Home Assistant configuration paths below a temporary root."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def path(self, *parts: str) -> str:
        """Return a path relative to the fake configuration directory."""
        return str(self._root.joinpath(*parts))


class FakeHomeAssistant:
    """Expose the configuration API used by SmartIRProvider."""

    def __init__(self, root: Path) -> None:
        self.config = FakeConfig(root)


def _provider(root: Path) -> SmartIRProvider:
    return SmartIRProvider(FakeHomeAssistant(root))  # type: ignore[arg-type]


def _codes_path(root: Path) -> Path:
    return root / "custom_components" / "smartir" / "codes"


def _write_code_file(
    root: Path,
    category: str,
    filename: str,
    commands: dict[str, Any],
    *,
    manufacturer: str = "Example",
    models: list[str] | None = None,
) -> Path:
    category_path = _codes_path(root) / category
    category_path.mkdir(parents=True, exist_ok=True)
    json_file = category_path / filename
    json_file.write_text(
        json.dumps(
            {
                "manufacturer": manufacturer,
                "supportedModels": models or ["Model One"],
                "supportedController": "Broadlink",
                "commands": commands,
            }
        ),
        encoding="utf-8",
    )
    return json_file


async def _collect(iterator: AsyncIterator[IRCode]) -> list[IRCode]:
    return [code async for code in iterator]


def test_missing_directory_returns_no_codes(tmp_path: Path) -> None:
    """A missing SmartIR installation behaves like an empty provider."""
    provider = _provider(tmp_path)

    codes = asyncio.run(_collect(provider.iter_codes()))

    assert codes == []
    assert provider.count() == 0


def test_empty_directory_returns_no_codes(tmp_path: Path) -> None:
    """An installed database with no categories yields no codes."""
    _codes_path(tmp_path).mkdir(parents=True)
    provider = _provider(tmp_path)

    assert asyncio.run(_collect(provider.iter_codes())) == []


def test_valid_json_generates_ir_codes(tmp_path: Path) -> None:
    """SmartIR metadata and command payloads are normalized into IRCode."""
    _write_code_file(
        tmp_path,
        "media_player",
        "1000.json",
        {"power": "power-payload", "volumeUp": "volume-payload"},
        manufacturer="Acme",
        models=["TV-1", "TV-2"],
    )

    codes = asyncio.run(_collect(_provider(tmp_path).iter_codes()))

    assert codes == [
        IRCode(
            name="power",
            payload="power-payload",
            manufacturer="Acme",
            model="TV-1",
            device_type="media_player",
        ),
        IRCode(
            name="volumeUp",
            payload="volume-payload",
            manufacturer="Acme",
            model="TV-1",
            device_type="media_player",
        ),
    ]


def test_nested_commands_are_flattened(tmp_path: Path) -> None:
    """Nested climate commands produce one independently named code per leaf."""
    _write_code_file(
        tmp_path,
        "climate",
        "2000.json",
        {"temp": {"24": "temp-24", "25": "temp-25"}, "fan": {"high": "fan"}},
    )

    codes = asyncio.run(_collect(_provider(tmp_path).iter_codes()))

    assert [(code.name, code.payload) for code in codes] == [
        ("temp24", "temp-24"),
        ("temp25", "temp-25"),
        ("fanHigh", "fan"),
    ]


def test_multiple_categories_and_files_are_discovered(tmp_path: Path) -> None:
    """Every immediate category and JSON file is loaded automatically."""
    _write_code_file(tmp_path, "fan", "1.json", {"power": "fan-power"})
    _write_code_file(tmp_path, "fan", "2.json", {"speed": "fan-speed"})
    _write_code_file(tmp_path, "light", "1.json", {"on": "light-on"})
    provider = _provider(tmp_path)

    codes = asyncio.run(_collect(provider.iter_codes()))

    assert {code.device_type for code in codes} == {"fan", "light"}
    assert {code.payload for code in codes} == {
        "fan-power",
        "fan-speed",
        "light-on",
    }
    assert provider.count() == 3


def test_corrupt_json_is_logged_and_skipped(tmp_path: Path, caplog: Any) -> None:
    """One corrupt file does not prevent other SmartIR files from loading."""
    _write_code_file(tmp_path, "fan", "valid.json", {"power": "valid"})
    corrupt = _codes_path(tmp_path) / "fan" / "corrupt.json"
    corrupt.write_text("{invalid", encoding="utf-8")

    with caplog.at_level(logging.WARNING):
        codes = asyncio.run(_collect(_provider(tmp_path).iter_codes()))

    assert [code.payload for code in codes] == ["valid"]
    assert "corrupt.json" in caplog.text


def test_cache_avoids_reloading_changed_files(tmp_path: Path) -> None:
    """Subsequent iterations reuse the first filesystem snapshot."""
    json_file = _write_code_file(tmp_path, "projector", "1.json", {"power": "original"})
    provider = _provider(tmp_path)
    first = asyncio.run(_collect(provider.iter_codes()))
    json_file.write_text("{invalid", encoding="utf-8")

    second = asyncio.run(_collect(provider.iter_codes()))

    assert second == first
    assert provider.count() == 1


def test_iteration_yields_every_code(tmp_path: Path) -> None:
    """The async iterator completes without dropping any command."""
    _write_code_file(
        tmp_path,
        "tv",
        "1.json",
        {f"command{index}": f"payload{index}" for index in range(5)},
    )
    provider = _provider(tmp_path)

    codes = asyncio.run(_collect(provider.iter_codes()))

    assert len(codes) == 5
    assert provider.count() == 5
