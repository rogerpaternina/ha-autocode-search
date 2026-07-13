"""Minimal Home Assistant stubs for integration tests."""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from typing import Any


class _Schema(dict[Any, Any]):
    """Minimal voluptuous schema replacement for flow tests."""


class _SelectSelectorConfig:
    """Store select selector configuration for flow tests."""

    def __init__(self, **kwargs: Any) -> None:
        """Store selector keyword arguments."""
        self.kwargs = kwargs


class _SelectSelector:
    """Store the select selector configuration for flow tests."""

    def __init__(self, config: _SelectSelectorConfig) -> None:
        """Store the selector configuration."""
        self.config = config


class _FlowBase:
    """Implement the Home Assistant flow result helpers used by the tests."""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Accept Home Assistant's domain keyword when subclasses are declared."""
        super().__init_subclass__()

    async def async_set_unique_id(self, unique_id: str) -> None:
        """Record the requested unique ID."""
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self) -> None:
        """Treat all fake test entities as not yet configured."""

    def async_show_form(self, **kwargs: Any) -> dict[str, Any]:
        """Return a form result matching Home Assistant's result shape."""
        return {"type": "form", **kwargs}

    def async_create_entry(self, **kwargs: Any) -> dict[str, Any]:
        """Return a create-entry result matching Home Assistant's result shape."""
        return {"type": "create_entry", **kwargs}

    def async_abort(self, **kwargs: Any) -> dict[str, Any]:
        """Return an abort result matching Home Assistant's result shape."""
        return {"type": "abort", **kwargs}


class _ConfigFlow(_FlowBase):
    """Minimal replacement for Home Assistant's ConfigFlow."""


class _OptionsFlowWithReload(_FlowBase):
    """Minimal replacement for Home Assistant's OptionsFlowWithReload."""


class _DataUpdateCoordinator:
    """Minimal DataUpdateCoordinator replacement for tests."""

    def __class_getitem__(cls, item: Any) -> type[_DataUpdateCoordinator]:
        """Support generic coordinator typing in integration modules."""
        return cls

    def __init__(
        self,
        hass: Any,
        logger: Any,
        name: str,
        update_interval: Any = None,
    ) -> None:
        """Store coordinator initialization arguments."""
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self.data: dict[str, Any] = {}

    async def async_config_entry_first_refresh(self) -> None:
        """Populate coordinator data from the update hook."""
        self.data = await self._async_update_data()

    def async_set_updated_data(self, data: dict[str, Any]) -> None:
        """Replace coordinator data."""
        self.data = data


class _CoordinatorEntity:
    """Minimal CoordinatorEntity replacement for tests."""

    def __class_getitem__(cls, item: Any) -> type[_CoordinatorEntity]:
        """Support generic entity typing in integration modules."""
        return cls

    def __init__(self, coordinator: _DataUpdateCoordinator) -> None:
        """Attach the entity to a coordinator."""
        self.coordinator = coordinator


class _SensorEntity:
    """Minimal SensorEntity replacement for tests."""


class _BinarySensorEntity:
    """Minimal BinarySensorEntity replacement for tests."""


class _HomeAssistantError(Exception):
    """Minimal HomeAssistantError replacement for tests."""


def install_home_assistant_stubs() -> None:
    """Install the Home Assistant API surface used by integration tests."""
    if "homeassistant.helpers.update_coordinator" in sys.modules:
        return

    homeassistant = ModuleType("homeassistant")
    config_entries = ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = SimpleNamespace
    config_entries.ConfigFlow = _ConfigFlow
    config_entries.OptionsFlowWithReload = _OptionsFlowWithReload
    core = ModuleType("homeassistant.core")
    core.callback = lambda function: function
    core.HomeAssistant = SimpleNamespace
    const = ModuleType("homeassistant.const")
    const.PERCENTAGE = "%"
    const.Platform = str
    exceptions = ModuleType("homeassistant.exceptions")
    exceptions.HomeAssistantError = _HomeAssistantError
    data_entry_flow = ModuleType("homeassistant.data_entry_flow")
    data_entry_flow.FlowResult = dict[str, Any]
    helpers = ModuleType("homeassistant.helpers")
    entity = ModuleType("homeassistant.helpers.entity")
    entity.EntityCategory = SimpleNamespace(DIAGNOSTIC="diagnostic")
    update_coordinator = ModuleType("homeassistant.helpers.update_coordinator")
    update_coordinator.DataUpdateCoordinator = _DataUpdateCoordinator
    update_coordinator.CoordinatorEntity = _CoordinatorEntity
    entity_platform = ModuleType("homeassistant.helpers.entity_platform")
    entity_platform.AddEntitiesCallback = Any
    selector = ModuleType("homeassistant.helpers.selector")
    selector.SelectSelector = _SelectSelector
    selector.SelectSelectorConfig = _SelectSelectorConfig
    selector.SelectSelectorMode = SimpleNamespace(DROPDOWN="dropdown")
    components = ModuleType("homeassistant.components")
    sensor = ModuleType("homeassistant.components.sensor")
    sensor.SensorEntity = _SensorEntity
    binary_sensor = ModuleType("homeassistant.components.binary_sensor")
    binary_sensor.BinarySensorEntity = _BinarySensorEntity

    voluptuous = ModuleType("voluptuous")
    voluptuous.Schema = _Schema
    voluptuous.Required = lambda key, default=None: key

    homeassistant.config_entries = config_entries
    homeassistant.core = core
    homeassistant.const = const
    homeassistant.exceptions = exceptions
    homeassistant.helpers = helpers
    helpers.entity = entity
    helpers.update_coordinator = update_coordinator
    helpers.entity_platform = entity_platform
    helpers.selector = selector
    homeassistant.components = components
    components.sensor = sensor
    components.binary_sensor = binary_sensor

    sys.modules.update(
        {
            "voluptuous": voluptuous,
            "homeassistant": homeassistant,
            "homeassistant.config_entries": config_entries,
            "homeassistant.core": core,
            "homeassistant.const": const,
            "homeassistant.exceptions": exceptions,
            "homeassistant.data_entry_flow": data_entry_flow,
            "homeassistant.helpers": helpers,
            "homeassistant.helpers.entity": entity,
            "homeassistant.helpers.update_coordinator": update_coordinator,
            "homeassistant.helpers.entity_platform": entity_platform,
            "homeassistant.helpers.selector": selector,
            "homeassistant.components": components,
            "homeassistant.components.sensor": sensor,
            "homeassistant.components.binary_sensor": binary_sensor,
        }
    )
