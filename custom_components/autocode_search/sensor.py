"""Sensor entities for Autocode Search."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import PERCENTAGE
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
    """Set up Autocode Search sensor entities."""
    coordinator: AutocodeSearchCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            AutocodeProgressSensor(coordinator, entry),
            AutocodeCodesTestedSensor(coordinator, entry),
            AutocodeTotalCodesSensor(coordinator, entry),
            AutocodeCurrentCommandSensor(coordinator, entry),
            AutocodeCurrentManufacturerSensor(coordinator, entry),
            AutocodeCurrentModelSensor(coordinator, entry),
            AutocodeElapsedTimeSensor(coordinator, entry),
            AutocodeFilterSummarySensor(coordinator, entry),
            AutocodeProvidersUsedSensor(coordinator, entry),
            AutocodeDuplicatesRemovedSensor(coordinator, entry),
            AutocodeProviderOrderSensor(coordinator, entry),
            AutocodeProviderRankingReasonSensor(coordinator, entry),
        ]
    )


class AutocodeSearchSensor(
    CoordinatorEntity["AutocodeSearchCoordinator"], SensorEntity
):
    """Base read-only sensor backed by the Autocode Search coordinator."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: AutocodeSearchCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the sensor from the coordinator and config entry."""
        super().__init__(coordinator)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "Autocode Search",
        }


class AutocodeProgressSensor(AutocodeSearchSensor):
    """Expose the current search progress percentage."""

    _attr_translation_key = "progress"
    _attr_unique_id = "autocode_progress"
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def native_value(self) -> float | None:
        """Return the current progress percentage."""
        return round(self.coordinator.data["progress"] * 100, 2)


class AutocodeCodesTestedSensor(AutocodeSearchSensor):
    """Expose how many codes have been tested."""

    _attr_translation_key = "codes_tested"
    _attr_unique_id = "autocode_codes_tested"

    @property
    def native_value(self) -> int:
        """Return the number of tested codes."""
        return self.coordinator.data["codes_tested"]


class AutocodeTotalCodesSensor(AutocodeSearchSensor):
    """Expose the total number of codes in the search."""

    _attr_translation_key = "total_codes"
    _attr_unique_id = "autocode_total_codes"

    @property
    def native_value(self) -> int:
        """Return the total number of codes in the active search."""
        return self.coordinator.data["codes_after_filter"]


class AutocodeCurrentCommandSensor(AutocodeSearchSensor):
    """Expose the command currently being tested."""

    _attr_translation_key = "current_command"
    _attr_unique_id = "autocode_current_command"

    @property
    def native_value(self) -> str | None:
        """Return the current command name."""
        return self.coordinator.data["current_code"]


class AutocodeCurrentManufacturerSensor(AutocodeSearchSensor):
    """Expose the manufacturer of the current code."""

    _attr_translation_key = "current_manufacturer"
    _attr_unique_id = "autocode_current_manufacturer"

    @property
    def native_value(self) -> str | None:
        """Return the current manufacturer."""
        return self.coordinator.data["current_manufacturer"]


class AutocodeCurrentModelSensor(AutocodeSearchSensor):
    """Expose the model of the current code."""

    _attr_translation_key = "current_model"
    _attr_unique_id = "autocode_current_model"

    @property
    def native_value(self) -> str | None:
        """Return the current model."""
        return self.coordinator.data["current_model"]


class AutocodeElapsedTimeSensor(AutocodeSearchSensor):
    """Expose the elapsed search time."""

    _attr_translation_key = "elapsed_time"
    _attr_unique_id = "autocode_elapsed_time"

    @property
    def native_value(self) -> str:
        """Return the formatted elapsed time."""
        return self.coordinator.data["elapsed_time"]


class AutocodeFilterSummarySensor(AutocodeSearchSensor):
    """Expose the active search filter as a compact summary."""

    _attr_translation_key = "filter_summary"
    _attr_unique_id = "autocode_filter_summary"

    @property
    def native_value(self) -> str:
        """Return the active filter summary."""
        return self.coordinator.data["filter_summary"]


class AutocodeProvidersUsedSensor(AutocodeSearchSensor):
    """Expose the code providers used by the active search."""

    _attr_translation_key = "providers_used"
    _attr_unique_id = "autocode_providers_used"

    @property
    def native_value(self) -> str:
        """Return the providers used, in priority order."""
        providers = self.coordinator.data["providers_used"]
        return ", ".join(providers) if providers else "None"


class AutocodeDuplicatesRemovedSensor(AutocodeSearchSensor):
    """Expose how many duplicate codes were removed across providers."""

    _attr_translation_key = "duplicates_removed"
    _attr_unique_id = "autocode_duplicates_removed"

    @property
    def native_value(self) -> int:
        """Return the number of removed duplicate codes."""
        return self.coordinator.data["duplicates_removed"]


class AutocodeProviderOrderSensor(AutocodeSearchSensor):
    """Expose the ranked provider consultation order."""

    _attr_translation_key = "provider_order"
    _attr_unique_id = "autocode_provider_order"

    @property
    def native_value(self) -> str:
        """Return the provider order as an arrow-separated list."""
        provider_order = self.coordinator.data["provider_order"]
        return " → ".join(provider_order) if provider_order else "None"


class AutocodeProviderRankingReasonSensor(AutocodeSearchSensor):
    """Expose why providers were ranked in the current order."""

    _attr_translation_key = "provider_ranking_reason"
    _attr_unique_id = "autocode_provider_ranking_reason"

    @property
    def native_value(self) -> str:
        """Return the ranking reason."""
        return self.coordinator.data["provider_ranking_reason"] or "None"
