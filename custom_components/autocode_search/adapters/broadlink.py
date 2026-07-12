"""Broadlink implementation of the infrared adapter interface."""

from __future__ import annotations

from typing import Any

from .base import IRAdapter


class BroadlinkAdapter(IRAdapter):
    """Provide a future adapter for Broadlink infrared devices."""

    async def send_code(self, code: str) -> None:
        """Send an infrared code through a Broadlink device."""
        # TODO: Add the Broadlink client and transmit the supplied code.
        raise NotImplementedError("Broadlink support has not been implemented")

    async def is_available(self) -> bool:
        """Return whether the configured Broadlink device is available."""
        # TODO: Add Broadlink reachability and authentication checks.
        raise NotImplementedError("Broadlink support has not been implemented")

    async def get_device_info(self) -> dict[str, Any]:
        """Return non-sensitive information about the Broadlink device."""
        # TODO: Return device information supplied by the Broadlink client.
        raise NotImplementedError("Broadlink support has not been implemented")

