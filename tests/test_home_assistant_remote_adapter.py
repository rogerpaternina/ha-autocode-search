"""Tests for the Home Assistant remote adapter."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.autocode_search.adapters.home_assistant_remote import (
    HomeAssistantRemoteAdapter,
)


def _create_hass(remote_state: MagicMock | None) -> MagicMock:
    """Create a mocked Home Assistant instance with a remote state."""
    hass = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.states.get.return_value = remote_state
    return hass


def test_send_code_calls_remote_send_command() -> None:
    """The adapter sends codes through Home Assistant's remote service."""
    hass = _create_hass(MagicMock())
    adapter = HomeAssistantRemoteAdapter(hass, "remote.living_room")

    asyncio.run(adapter.send_code("JgBQAAAB"))

    hass.services.async_call.assert_awaited_once_with(
        "remote",
        "send_command",
        {
            "entity_id": "remote.living_room",
            "command": "JgBQAAAB",
        },
        blocking=True,
    )


def test_broadlink_packet_is_sent_with_base64_prefix() -> None:
    """A native Broadlink packet is sent with Home Assistant's b64 prefix."""
    hass = _create_hass(MagicMock())
    adapter = HomeAssistantRemoteAdapter(hass, "remote.living_room")

    with patch.object(adapter, "_is_broadlink_remote", return_value=True):
        asyncio.run(adapter.send_code("JgBQAAAB"))

    hass.services.async_call.assert_awaited_once_with(
        "remote",
        "send_command",
        {
            "entity_id": "remote.living_room",
            "command": "b64:JgBQAAAB",
        },
        blocking=True,
    )


def test_broadlink_named_command_uses_generic_strategy() -> None:
    """A learned command name remains unchanged for backward compatibility."""
    hass = _create_hass(MagicMock())
    adapter = HomeAssistantRemoteAdapter(hass, "remote.living_room")

    with patch.object(adapter, "_is_broadlink_remote", return_value=True):
        asyncio.run(adapter.send_code("power"))

    hass.services.async_call.assert_awaited_once_with(
        "remote",
        "send_command",
        {
            "entity_id": "remote.living_room",
            "command": "power",
        },
        blocking=True,
    )


def test_is_available_checks_for_existing_entity() -> None:
    """The adapter is available only when the remote entity exists."""
    available_hass = _create_hass(MagicMock())
    unavailable_hass = _create_hass(None)

    available_adapter = HomeAssistantRemoteAdapter(available_hass, "remote.living_room")
    unavailable_adapter = HomeAssistantRemoteAdapter(unavailable_hass, "remote.missing")

    assert asyncio.run(available_adapter.is_available())
    assert not asyncio.run(unavailable_adapter.is_available())


def test_get_device_info_returns_remote_state_details() -> None:
    """The adapter exposes basic information from the remote entity state."""
    remote_state = MagicMock()
    remote_state.attributes = {"friendly_name": "Living Room Remote"}
    remote_state.state = "on"
    hass = _create_hass(remote_state)
    adapter = HomeAssistantRemoteAdapter(hass, "remote.living_room")

    device_info = asyncio.run(adapter.get_device_info())

    assert device_info == {
        "entity_id": "remote.living_room",
        "friendly_name": "Living Room Remote",
        "state": "on",
    }
