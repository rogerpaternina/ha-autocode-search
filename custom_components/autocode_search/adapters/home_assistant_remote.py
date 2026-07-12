"""Adapter for Home Assistant remote entities."""

from __future__ import annotations

from abc import ABC, abstractmethod
from base64 import b64decode
from binascii import Error as BinasciiError
from typing import TYPE_CHECKING, Any

from .base import IRAdapter

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


class RemoteCommandStrategy(ABC):
    """Define how an IR code is represented for a remote entity."""

    @abstractmethod
    async def async_send(
        self, hass: HomeAssistant, entity_id: str, code: str
    ) -> None:
        """Send a code through the supplied Home Assistant remote entity."""


class GenericStrategy(RemoteCommandStrategy):
    """Send codes unchanged for generic Home Assistant remote entities."""

    async def async_send(
        self, hass: HomeAssistant, entity_id: str, code: str
    ) -> None:
        """Send a code using the standard remote command representation."""
        await hass.services.async_call(
            "remote",
            "send_command",
            {
                "entity_id": entity_id,
                "command": code,
            },
            blocking=True,
        )


class BroadlinkRawStrategy(RemoteCommandStrategy):
    """Send native Base64 Broadlink packets through a Broadlink remote."""

    _PACKET_TYPES = frozenset((0x26, 0xB2, 0xD7))

    @classmethod
    def can_handle(cls, code: str) -> bool:
        """Return whether a code is an explicit or recognizable Broadlink packet."""
        if code.startswith("b64:"):
            return True

        try:
            packet = b64decode(code + ("=" * (-len(code) % 4)), validate=True)
        except BinasciiError:
            return False

        return bool(packet) and packet[0] in cls._PACKET_TYPES

    async def async_send(
        self, hass: HomeAssistant, entity_id: str, code: str
    ) -> None:
        """Send a native Broadlink packet with Home Assistant's ``b64:`` syntax."""
        payload = code.removeprefix("b64:")
        await hass.services.async_call(
            "remote",
            "send_command",
            {
                "entity_id": entity_id,
                "command": f"b64:{payload}",
            },
            blocking=True,
        )


class HomeAssistantRemoteAdapter(IRAdapter):
    """Send infrared codes through any Home Assistant ``remote`` entity.

    The entity must support the standard ``remote.send_command`` service. This
    keeps the search engine independent of the remote integration or hardware
    behind that entity.
    """

    def __init__(self, hass: HomeAssistant, entity_id: str) -> None:
        """Initialize the adapter for a Home Assistant remote entity."""
        self._hass = hass
        self._entity_id = entity_id
        self._generic_strategy = GenericStrategy()
        self._broadlink_strategy = BroadlinkRawStrategy()

    async def send_code(self, code: str) -> None:
        """Send an infrared code through the configured remote entity."""
        strategy = self._select_strategy(code)
        await strategy.async_send(self._hass, self._entity_id, code)

    def _select_strategy(self, code: str) -> RemoteCommandStrategy:
        """Select the packet strategy that matches the entity and code."""
        if self._is_broadlink_remote() and self._broadlink_strategy.can_handle(code):
            return self._broadlink_strategy
        return self._generic_strategy

    def _is_broadlink_remote(self) -> bool:
        """Return whether the remote entity is provided by the Broadlink integration."""
        try:
            from homeassistant.helpers import entity_registry as er
        except ImportError:
            # Allow pure-Python tests to exercise the adapter without Home Assistant.
            return False

        entry = er.async_get(self._hass).async_get(self._entity_id)
        return entry is not None and entry.platform == "broadlink"

    async def is_available(self) -> bool:
        """Return whether the configured remote entity exists in Home Assistant."""
        return self._hass.states.get(self._entity_id) is not None

    async def get_device_info(self) -> dict[str, Any]:
        """Return non-sensitive state information for the remote entity."""
        remote_state = self._hass.states.get(self._entity_id)
        if remote_state is None:
            return {
                "entity_id": self._entity_id,
                "friendly_name": None,
                "state": None,
            }

        return {
            "entity_id": self._entity_id,
            "friendly_name": remote_state.attributes.get("friendly_name"),
            "state": remote_state.state,
        }
