"""Binary sensor entities for Autocode Search."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .models import SearchStatus

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import AutocodeSearchCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Autocode Search binary sensor entities."""
    coordinator: AutocodeSearchCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            AutocodeRunningBinarySensor(coordinator, entry),
            AutocodeWaitingConfirmationBinarySensor(coordinator, entry),
        ]
    )


class AutocodeRunningBinarySensor(
    CoordinatorEntity["AutocodeSearchCoordinator"], BinarySensorEntity
):
    """Indicate whether an Autocode Search session is actively running."""

    _attr_has_entity_name = True
    _attr_translation_key = "running"
    _attr_unique_id = "autocode_running"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: AutocodeSearchCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the binary sensor from the coordinator and config entry."""
        super().__init__(coordinator)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Autocode Search",
        }

    @property
    def is_on(self) -> bool:
        """Return whether the search is currently running."""
        return self.coordinator.data["search_status"] == SearchStatus.RUNNING.value


class AutocodeWaitingConfirmationBinarySensor(
    CoordinatorEntity["AutocodeSearchCoordinator"], BinarySensorEntity
):
    """Indicate whether the integration awaits user confirmation."""

    _attr_has_entity_name = True
    _attr_translation_key = "waiting_confirmation"
    _attr_unique_id = "autocode_waiting_confirmation"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: AutocodeSearchCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the binary sensor from the coordinator and config entry."""
        super().__init__(coordinator)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Autocode Search",
        }

    @property
    def is_on(self) -> bool:
        """Return whether a search result awaits user confirmation."""
        return bool(self.coordinator.data["awaiting_confirmation"])
