"""Backward-compatible alias for the Home Assistant remote adapter."""

from __future__ import annotations

from .home_assistant_remote import HomeAssistantRemoteAdapter


class BroadlinkAdapter(HomeAssistantRemoteAdapter):
    """Deprecated compatibility name for ``HomeAssistantRemoteAdapter``.

    Use ``HomeAssistantRemoteAdapter`` for any Home Assistant remote entity,
    including entities backed by Broadlink hardware.
    """
