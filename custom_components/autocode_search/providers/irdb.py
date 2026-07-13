"""Provider for locally installed IRDB infrared code databases."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import TYPE_CHECKING

from ..models.ir_code import IRCode
from ..models.search_filter import SearchFilter
from .base import CodeProvider
from .filtering import filter_codes
from .irdb_paths import resolve_irdb_database_path
from .irdb_reader import read_irdb_database

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class IRDBProvider(CodeProvider):
    """Read and normalize every code in a locally installed IRDB database."""

    def __init__(self, hass: HomeAssistant | None = None) -> None:
        """Initialize the provider without touching the filesystem."""
        self._hass = hass
        self._cache: list[IRCode] | None = None
        self._active_codes: list[IRCode] = []
        self._index = 0

    async def load(self, search_filter: SearchFilter | None = None) -> None:
        """Load IRDB codes once and apply the optional search filter."""
        if self._cache is None:
            database_path = self._database_path()
            self._cache = await asyncio.to_thread(self._read_codes, database_path)

        self._apply_filter(search_filter)
        self.reset()

    async def iter_codes(
        self,
        search_filter: SearchFilter | None = None,
    ) -> AsyncIterator[IRCode]:
        """Yield IRDB codes that match the optional search filter."""
        await self.load(search_filter)
        for code in self._active_codes:
            _LOGGER.debug("Yielding %s", code.name)
            yield code

    def current(self) -> IRCode | None:
        """Return the current IRDB code."""
        if not self._active_codes:
            return None
        return self._active_codes[self._index]

    def next(self) -> IRCode | None:
        """Advance to and return the next IRDB code."""
        if not self._active_codes or self._index >= len(self._active_codes) - 1:
            return None
        self._index += 1
        return self.current()

    def previous(self) -> IRCode | None:
        """Move back to and return the previous IRDB code."""
        if not self._active_codes or self._index == 0:
            return None
        self._index -= 1
        return self.current()

    def count(self) -> int:
        """Return the number of IRDB codes available after filtering."""
        return len(self._active_codes)

    def unfiltered_count(self) -> int:
        """Return the number of IRDB codes before filtering."""
        return len(self._cache or ())

    def reset(self) -> None:
        """Reset the IRDB cursor to its initial position."""
        self._index = 0

    def clear_cache(self) -> None:
        """Invalidate the cached IRDB database."""
        self._cache = None
        self._active_codes = []
        self._index = 0

    def _database_path(self) -> Path:
        if self._hass is None:
            raise RuntimeError("Home Assistant is required to locate the IRDB database")
        return resolve_irdb_database_path(self._hass)

    def _read_codes(self, database_path: Path) -> list[IRCode]:
        if not database_path.is_dir():
            _LOGGER.warning("IRDB database not found: %s", database_path)
            return []

        _LOGGER.debug("IRDB database found: %s", database_path)
        return read_irdb_database(database_path)

    def _apply_filter(self, search_filter: SearchFilter | None) -> None:
        """Apply the search filter to the cached IRDB codes."""
        assert self._cache is not None
        before_count = len(self._cache)

        if search_filter is not None and search_filter.is_active():
            _LOGGER.debug("Applying filter")
            if search_filter.manufacturer:
                _LOGGER.debug("Manufacturer: %s", search_filter.manufacturer.upper())
            if search_filter.device_type:
                _LOGGER.debug("Device Type: %s", search_filter.device_type.upper())
            if search_filter.command:
                _LOGGER.debug("Command: %s", search_filter.command.upper())
            if search_filter.model:
                _LOGGER.debug("Model: %s", search_filter.model.upper())
            _LOGGER.debug("Codes before filter: %s", before_count)

        self._active_codes = filter_codes(self._cache, search_filter)

        if search_filter is not None and search_filter.is_active():
            _LOGGER.debug("Codes after filter: %s", len(self._active_codes))
