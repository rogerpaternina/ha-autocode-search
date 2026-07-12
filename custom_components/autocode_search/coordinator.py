"""Data coordinator for Autocode Search."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class AutocodeSearchCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate future IR-code searches and shared integration data."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=None,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Return the latest shared data for the integration."""
        # TODO: Implement the IR-code search engine and return its results.
        return {"status": "ready"}
