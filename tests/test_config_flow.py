"""Tests for the Autocode Search configuration and options flows."""

from __future__ import annotations

import asyncio
import importlib
import sys
from dataclasses import dataclass
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


def _install_home_assistant_flow_stubs() -> None:
    """Install the small Home Assistant API surface used by config_flow tests."""
    voluptuous = ModuleType("voluptuous")
    voluptuous.Schema = _Schema
    voluptuous.Required = lambda key, default=None: key
    sys.modules["voluptuous"] = voluptuous

    homeassistant = ModuleType("homeassistant")
    config_entries = ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = SimpleNamespace
    config_entries.ConfigFlow = _ConfigFlow
    config_entries.OptionsFlowWithReload = _OptionsFlowWithReload
    core = ModuleType("homeassistant.core")
    core.callback = lambda function: function
    data_entry_flow = ModuleType("homeassistant.data_entry_flow")
    data_entry_flow.FlowResult = dict[str, Any]
    helpers = ModuleType("homeassistant.helpers")
    selector = ModuleType("homeassistant.helpers.selector")
    selector.SelectSelector = _SelectSelector
    selector.SelectSelectorConfig = _SelectSelectorConfig
    selector.SelectSelectorMode = SimpleNamespace(DROPDOWN="dropdown")

    homeassistant.config_entries = config_entries
    homeassistant.core = core
    sys.modules.update(
        {
            "homeassistant": homeassistant,
            "homeassistant.config_entries": config_entries,
            "homeassistant.core": core,
            "homeassistant.data_entry_flow": data_entry_flow,
            "homeassistant.helpers": helpers,
            "homeassistant.helpers.selector": selector,
        }
    )


_install_home_assistant_flow_stubs()
config_flow = importlib.import_module("custom_components.autocode_search.config_flow")


@dataclass
class _State:
    """Minimal state object returned by the fake Home Assistant state machine."""

    entity_id: str


class _States:
    """Expose remote states through the Home Assistant state-machine API."""

    def __init__(self, entity_ids: list[str]) -> None:
        """Initialize available state objects."""
        self._states = [_State(entity_id) for entity_id in entity_ids]

    def async_all(self, domain: str) -> list[_State]:
        """Return states that match the requested domain."""
        return [state for state in self._states if state.entity_id.startswith(f"{domain}.")]

    def get(self, entity_id: str) -> _State | None:
        """Return a state by entity ID."""
        return next((state for state in self._states if state.entity_id == entity_id), None)


class _Hass:
    """Minimal Home Assistant instance for config-flow tests."""

    def __init__(self, entity_ids: list[str]) -> None:
        """Initialize the fake state machine."""
        self.states = _States(entity_ids)


def _new_config_flow(entity_ids: list[str]) -> Any:
    """Create a config flow with a fake Home Assistant instance."""
    flow = config_flow.AutocodeSearchConfigFlow()
    flow.hass = _Hass(entity_ids)
    return flow


def test_config_flow_creates_entry_with_all_configuration() -> None:
    """The four configuration steps create an entry with the requested data."""
    flow = _new_config_flow(["remote.living_room"])

    result = asyncio.run(flow.async_step_user({"entity_id": "remote.living_room"}))
    assert result["step_id"] == "device_type"
    result = asyncio.run(flow.async_step_device_type({"device_type": "tv"}))
    assert result["step_id"] == "brand"
    result = asyncio.run(flow.async_step_brand({"brand": "samsung"}))
    assert result["step_id"] == "provider"
    result = asyncio.run(flow.async_step_provider({"provider": "auto"}))

    assert result == {
        "type": "create_entry",
        "title": "Autocode Search",
        "data": {
            "entity_id": "remote.living_room",
            "device_type": "tv",
            "brand": "samsung",
            "provider": "auto",
        },
    }


def test_config_flow_aborts_without_remote_entities() -> None:
    """The flow clearly aborts when Home Assistant has no remote entities."""
    flow = _new_config_flow([])

    result = asyncio.run(flow.async_step_user())

    assert result == {"type": "abort", "reason": "no_remote_entities"}


def test_config_flow_rejects_invalid_remote_and_provider() -> None:
    """The flow returns translated error keys for invalid user input."""
    flow = _new_config_flow(["remote.living_room"])

    result = asyncio.run(flow.async_step_user({"entity_id": "switch.invalid"}))
    assert result["errors"] == {"entity_id": "invalid_remote"}
    result = asyncio.run(flow.async_step_provider({"provider": "unknown"}))
    assert result["errors"] == {"provider": "invalid_provider"}


def test_options_flow_updates_all_configuration_values() -> None:
    """The options flow stores updated remote, type, brand, and provider values."""
    flow = config_flow.AutocodeSearchOptionsFlow()
    flow.hass = _Hass(["remote.living_room", "remote.bedroom"])
    flow.config_entry = SimpleNamespace(
        data={
            "entity_id": "remote.living_room",
            "device_type": "tv",
            "brand": "samsung",
            "provider": "auto",
        },
        options={},
    )

    result = asyncio.run(flow.async_step_init({"entity_id": "remote.bedroom"}))
    assert result["step_id"] == "device_type"
    asyncio.run(flow.async_step_device_type({"device_type": "fan"}))
    asyncio.run(flow.async_step_brand({"brand": "gree"}))
    result = asyncio.run(flow.async_step_provider({"provider": "lirc"}))

    assert result["type"] == "create_entry"
    assert result["data"] == {
        "entity_id": "remote.bedroom",
        "device_type": "fan",
        "brand": "gree",
        "provider": "lirc",
    }
