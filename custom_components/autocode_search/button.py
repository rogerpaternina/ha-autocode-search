"""Button entities for Autocode Search user confirmation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

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
    """Set up Autocode Search button entities."""
    coordinator: AutocodeSearchCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            AutocodeConfirmSuccessButton(coordinator, entry),
            AutocodeRejectResultButton(coordinator, entry),
        ]
    )


class AutocodeSearchButton(
    CoordinatorEntity["AutocodeSearchCoordinator"], ButtonEntity
):
    """Base button backed by the Autocode Search coordinator."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator: AutocodeSearchCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the button from the coordinator and config entry."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Autocode Search",
        }

    async def _async_call_service(self, service: str) -> None:
        """Invoke a domain service for this button press."""
        await self.coordinator.hass.services.async_call(
            DOMAIN,
            service,
            {},
            blocking=True,
        )


class AutocodeConfirmSuccessButton(AutocodeSearchButton):
    """Confirm that the last tested infrared code worked."""

    _attr_translation_key = "confirm_success"
    _attr_unique_id = "autocode_confirm_success"

    async def async_press(self) -> None:
        """Record the last tested code as a successful result."""
        await self._async_call_service("confirm_success")


class AutocodeRejectResultButton(AutocodeSearchButton):
    """Reject the last tested infrared code without learning."""

    _attr_translation_key = "reject_result"
    _attr_unique_id = "autocode_reject_result"

    async def async_press(self) -> None:
        """Dismiss the pending confirmation without storing a success."""
        await self._async_call_service("reject_result")
