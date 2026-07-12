"""Adapter for Home Assistant remote entities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import IRAdapter

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


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

    async def send_code(self, code: str) -> None:
        """Send an infrared code through the configured remote entity."""
        await self._hass.services.async_call(
            "remote",
            "send_command",
            {
                "entity_id": self._entity_id,
                "command": code,
            },
            blocking=True,
        )

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
