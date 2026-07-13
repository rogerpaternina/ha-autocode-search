"""Centralized LIRC database path configuration."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

LIRC_DATABASE_PATH_PARTS: tuple[str, ...] = ("lirc",)
LIRC_REMOTES_PATH_PARTS: tuple[str, ...] = ("lirc", "remotes")


def resolve_lirc_database_path(hass: HomeAssistant) -> Path:
    """Return the configured LIRC database path for a Home Assistant instance."""
    remotes_path = Path(hass.config.path(*LIRC_REMOTES_PATH_PARTS))
    if remotes_path.is_dir():
        return remotes_path
    return Path(hass.config.path(*LIRC_DATABASE_PATH_PARTS))
