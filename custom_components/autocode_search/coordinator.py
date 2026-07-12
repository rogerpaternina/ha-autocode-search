"""Data coordinator for Autocode Search."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, TypedDict
from uuid import uuid4

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .adapters.base import IRAdapter
from .const import DOMAIN
from .engine import SearchEngine
from .models import SearchSession, SearchStatus
from .providers.base import CodeProvider

_LOGGER = logging.getLogger(__name__)


class AutocodeSearchData(TypedDict):
    """Represent the shared data exposed by the coordinator."""

    status: str
    adapter_available: bool | None
    device_info: dict[str, Any] | None


class AutocodeSearchCoordinator(DataUpdateCoordinator[AutocodeSearchData]):
    """Coordinate future IR-code searches and shared integration data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator from a Home Assistant config entry.

        Options override the original config-entry data so reconfiguration takes
        effect after the options flow reloads this integration.
        """
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=None,
        )
        self.config_entry = entry
        self.configuration: dict[str, Any] = {**entry.data, **entry.options}
        self.adapter: IRAdapter | None = None
        self.search_engine: SearchEngine | None = None
        now = datetime.now(timezone.utc)
        # TODO: Replace this idle session when the search flow creates one.
        self.search_session = SearchSession(
            session_id=str(uuid4()),
            device_type="",
            brand="",
            command="",
            current_index=0,
            total_codes=0,
            status=SearchStatus.IDLE,
            started_at=now,
            last_update=now,
        )
        # TODO: Initialize a SearchEngine from the configured provider and remote.

    async def async_start_search(
        self,
        provider: CodeProvider,
        adapter: IRAdapter,
        session: SearchSession,
    ) -> SearchEngine:
        """Create, start, and retain the search engine for a new session."""
        engine = SearchEngine(provider, adapter, session)
        await engine.start()
        self.adapter = adapter
        self.search_session = session
        self.search_engine = engine
        return engine

    async def _async_update_data(self) -> AutocodeSearchData:
        """Return the latest shared data for the integration."""
        if self.adapter is None:
            # TODO: Inject an adapter after hardware configuration is implemented.
            # TODO: Start and advance self.search_session from the search engine.
            return {
                "status": "adapter_not_configured",
                "adapter_available": None,
                "device_info": None,
            }

        return {
            "status": "ready",
            "adapter_available": await self.adapter.is_available(),
            "device_info": await self.adapter.get_device_info(),
        }
