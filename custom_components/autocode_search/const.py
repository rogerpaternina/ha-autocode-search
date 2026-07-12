"""Constants for the Autocode Search integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.const import Platform

DOMAIN = "autocode_search"
NAME = "Autocode Search"

# TODO: Add platforms here as entities are implemented.
PLATFORMS: list[Platform] = []
