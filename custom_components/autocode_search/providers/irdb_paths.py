"""Centralized IRDB database path configuration."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

IRDB_DATABASE_PATH_PARTS: tuple[str, ...] = ("irdb", "codes")


def resolve_irdb_database_path(hass: HomeAssistant) -> Path:
    """Return the configured IRDB database path for a Home Assistant instance."""
    return Path(hass.config.path(*IRDB_DATABASE_PATH_PARTS))
