"""Tests for the Autocode Search configuration and options flows."""

from __future__ import annotations

import asyncio
import importlib
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

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
        return [
            state for state in self._states if state.entity_id.startswith(f"{domain}.")
        ]

    def get(self, entity_id: str) -> _State | None:
        """Return a state by entity ID."""
        return next(
            (state for state in self._states if state.entity_id == entity_id), None
        )


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
