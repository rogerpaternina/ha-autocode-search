"""Provider for code databases installed by the SmartIR integration."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Iterator, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..models.ir_code import IRCode
from .base import CodeProvider

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class SmartIRProvider(CodeProvider):
    """Read and normalize every code in an installed SmartIR database."""

    def __init__(self, hass: HomeAssistant | None = None) -> None:
        """Initialize the provider without touching the filesystem."""
        self._hass = hass
        self._cache: list[IRCode] | None = None
        self._index = 0

    async def load(self) -> None:
        """Load SmartIR codes once and reset the cursor."""
        if self._cache is None:
            codes_path = self._codes_path()
            self._cache = await asyncio.to_thread(self._read_codes, codes_path)
        self.reset()

    async def iter_codes(self) -> AsyncIterator[IRCode]:
        """Yield all SmartIR codes, reusing the cached database after first load."""
        await self.load()
        assert self._cache is not None
        for code in self._cache:
            _LOGGER.debug("Yielding %s", code.name)
            yield code

    def current(self) -> IRCode | None:
        """Return the current SmartIR code."""
        if not self._cache:
            return None
        return self._cache[self._index]

    def next(self) -> IRCode | None:
        """Advance to and return the next SmartIR code."""
        if not self._cache or self._index >= len(self._cache) - 1:
            return None
        self._index += 1
        return self.current()

    def previous(self) -> IRCode | None:
        """Move back to and return the previous SmartIR code."""
        if not self._cache or self._index == 0:
            return None
        self._index -= 1
        return self.current()

    def count(self) -> int:
        """Return the number of SmartIR codes available."""
        return len(self._cache or ())

    def reset(self) -> None:
        """Reset the SmartIR cursor."""
        self._index = 0

    def _codes_path(self) -> Path:
        if self._hass is None:
            raise RuntimeError("Home Assistant is required to locate SmartIR codes")
        return Path(self._hass.config.path("custom_components", "smartir", "codes"))

    def _read_codes(self, codes_path: Path) -> list[IRCode]:
        codes: list[IRCode] = []
        loaded_files = 0

        if not codes_path.is_dir():
            _LOGGER.warning("SmartIR codes directory not found: %s", codes_path)
            return codes

        _LOGGER.debug("SmartIR codes directory found: %s", codes_path)
        for category in sorted(codes_path.iterdir()):
            if not category.is_dir():
                continue

            _LOGGER.debug("Loading category %s", category.name)
            for json_file in sorted(category.glob("*.json")):
                file_codes = self._read_file(json_file, category.name)
                if file_codes is None:
                    continue
                loaded_files += 1
                codes.extend(file_codes)

        _LOGGER.debug("Loaded %d JSON files", loaded_files)
        _LOGGER.debug("Loaded %d IR codes", len(codes))
        return codes

    def _read_file(self, json_file: Path, device_type: str) -> list[IRCode] | None:
        try:
            with json_file.open(encoding="utf-8") as file:
                raw_data: Any = json.load(file)
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as err:
            _LOGGER.warning("Unable to load SmartIR file %s: %s", json_file, err)
            return None

        if not isinstance(raw_data, dict):
            _LOGGER.warning("Invalid SmartIR file %s: expected an object", json_file)
            return None

        data: dict[str, Any] = raw_data
        commands = data.get("commands")
        if not isinstance(commands, dict):
            _LOGGER.warning(
                "Invalid SmartIR file %s: missing commands object", json_file
            )
            return None

        manufacturer = _optional_string(data.get("manufacturer"))
        model = _first_model(data.get("supportedModels"))
        protocol = _optional_string(data.get("protocol"))

        return [
            IRCode(
                name=name,
                payload=payload,
                protocol=protocol,
                manufacturer=manufacturer,
                model=model,
                device_type=device_type,
            )
            for name, payload in _iter_commands(commands)
        ]


def _iter_commands(
    commands: Mapping[str, Any], prefix: tuple[str, ...] = ()
) -> Iterator[tuple[str, str]]:
    """Flatten nested SmartIR commands into named payloads."""
    for command, value in commands.items():
        path = (*prefix, command)
        if isinstance(value, str):
            yield _command_name(path), value
        elif isinstance(value, dict):
            yield from _iter_commands(value, path)


def _command_name(parts: tuple[str, ...]) -> str:
    first, *rest = parts
    return first + "".join(part[:1].upper() + part[1:] for part in rest)


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _first_model(value: object) -> str | None:
    if isinstance(value, list):
        return next((model for model in value if isinstance(model, str)), None)
    return _optional_string(value)
