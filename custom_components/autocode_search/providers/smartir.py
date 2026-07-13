"""Provider for code databases installed by the SmartIR integration."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Iterator, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..models.ir_code import IRCode
from ..models.search_filter import SearchFilter
from .base import CodeProvider
from .filtering import filter_codes

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class SmartIRProvider(CodeProvider):
    """Read and normalize every code in an installed SmartIR database."""

    def __init__(self, hass: HomeAssistant | None = None) -> None:
        """Initialize the provider without touching the filesystem."""
        self._hass = hass
        self._cache: list[IRCode] | None = None
        self._active_codes: list[IRCode] = []
        self._index = 0

    async def load(self, search_filter: SearchFilter | None = None) -> None:
        """Load SmartIR codes once and apply the optional search filter."""
        if self._cache is None:
            codes_path = self._codes_path()
            self._cache = await asyncio.to_thread(self._read_codes, codes_path)

        self._apply_filter(search_filter)
        self.reset()

    async def iter_codes(
        self,
        search_filter: SearchFilter | None = None,
    ) -> AsyncIterator[IRCode]:
        """Yield SmartIR codes that match the optional search filter."""
        await self.load(search_filter)
        for code in self._active_codes:
            _LOGGER.debug("Yielding %s", code.name)
            yield code

    def current(self) -> IRCode | None:
        """Return the current SmartIR code."""
        if not self._active_codes:
            return None
        return self._active_codes[self._index]

    def next(self) -> IRCode | None:
        """Advance to and return the next SmartIR code."""
        if not self._active_codes or self._index >= len(self._active_codes) - 1:
            return None
        self._index += 1
        return self.current()

    def previous(self) -> IRCode | None:
        """Move back to and return the previous SmartIR code."""
        if not self._active_codes or self._index == 0:
            return None
        self._index -= 1
        return self.current()

    def count(self) -> int:
        """Return the number of SmartIR codes available after filtering."""
        return len(self._active_codes)

    def unfiltered_count(self) -> int:
        """Return the number of SmartIR codes before filtering."""
        return len(self._cache or ())

    def reset(self) -> None:
        """Reset the SmartIR cursor."""
        self._index = 0

    def _apply_filter(self, search_filter: SearchFilter | None) -> None:
        """Apply the search filter to the cached SmartIR codes."""
        assert self._cache is not None
        before_count = len(self._cache)

        if search_filter is not None and search_filter.is_active():
            _LOGGER.debug("Applying search filter")
            if search_filter.manufacturer:
                _LOGGER.debug("Manufacturer: %s", search_filter.manufacturer.upper())
            if search_filter.device_type:
                _LOGGER.debug("Device Type: %s", search_filter.device_type.upper())
            if search_filter.command:
                _LOGGER.debug("Command: %s", search_filter.command.upper())
            if search_filter.model:
                _LOGGER.debug("Model: %s", search_filter.model.upper())
            _LOGGER.debug("SmartIR codes before filter: %s", before_count)

        self._active_codes = filter_codes(self._cache, search_filter)

        if search_filter is not None and search_filter.is_active():
            _LOGGER.debug("SmartIR codes after filter: %s", len(self._active_codes))

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
        supported_models = _supported_models(data.get("supportedModels"))
        model = supported_models[0] if supported_models else None
        protocol = _optional_string(data.get("protocol"))

        return [
            IRCode(
                name=name,
                payload=payload,
                protocol=protocol,
                manufacturer=manufacturer,
                model=model,
                device_type=device_type,
                supported_models=supported_models,
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


def _supported_models(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, list):
        return None

    models = tuple(model for model in value if isinstance(model, str) and model)
    return models or None
