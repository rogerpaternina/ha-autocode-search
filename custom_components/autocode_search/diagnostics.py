"""Diagnostics support for Autocode Search."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import AutocodeSearchCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: AutocodeSearchCoordinator = hass.data[DOMAIN][entry.entry_id]

    return {
        "entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "version": entry.version,
        },
        "coordinator_data": coordinator.data,
        # TODO: Redact search-provider configuration if it is added in the future.
    }
