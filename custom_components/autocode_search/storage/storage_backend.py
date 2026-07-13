"""Home Assistant storage backend for success memory."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers.storage import Store

from ..memory.success_memory import SuccessMemory
from .success_repository import STORAGE_VERSION, SuccessRepository

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from ..memory.models import SuccessRecord

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY = "autocode_search.success_memory"


class StorageBackend:
    """Persist success-memory records through the Home Assistant Storage API."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the storage backend for the given Home Assistant instance."""
        self._hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._repository = SuccessRepository()

    async def async_load(self) -> list[SuccessRecord]:
        """Load success records from Home Assistant storage."""
        _LOGGER.debug("Loading Success Memory")
        payload = await self._store.async_load()
        records = self._repository.from_payload(payload)
        _LOGGER.debug("Loaded %d records", len(records))
        return records

    async def async_save(self, records: list[SuccessRecord]) -> None:
        """Persist success records to Home Assistant storage."""
        if records:
            _LOGGER.debug("Saving Success Memory")
            await self._store.async_save(self._repository.to_payload(records))
            _LOGGER.debug("%d records stored", len(records))
            return

        _LOGGER.debug("Storage cleared")
        await self._store.async_save(self._repository.to_payload([]))

    def attach(self, memory: SuccessMemory) -> None:
        """Bind persistence callbacks to a success-memory instance."""
        memory.set_persist_callback(self._schedule_save)

    def _schedule_save(self, records: list[SuccessRecord]) -> None:
        self._hass.async_create_task(self.async_save(records))
