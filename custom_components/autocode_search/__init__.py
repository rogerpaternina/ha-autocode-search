"""Set up the Autocode Search integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Autocode Search from a config entry."""
    from .const import DOMAIN, PLATFORMS
    from .coordinator import AutocodeSearchCoordinator
    from .services import async_setup_services

    coordinator = AutocodeSearchCoordinator(hass)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await async_setup_services(hass)

    # TODO: Add entity platforms when the integration exposes entities.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Autocode Search config entry."""
    from .const import DOMAIN, PLATFORMS
    from .services import async_unload_services

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        await async_unload_services(hass)

    return unload_ok
