"""Constants for the Autocode Search integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.const import Platform

DOMAIN = "autocode_search"
NAME = "Autocode Search"

CONF_BRAND = "brand"
CONF_DEVICE_TYPE = "device_type"
CONF_ENTITY_ID = "entity_id"
CONF_PROVIDER = "provider"

DEVICE_TYPES: tuple[str, ...] = (
    "tv",
    "air_conditioner",
    "fan",
    "av_receiver",
    "projector",
    "set_top_box",
    "audio_system",
    "other",
)

# Keep this tuple as the single, easy-to-extend catalog of initial brands.
BRANDS: tuple[str, ...] = (
    "samsung",
    "lg",
    "sony",
    "panasonic",
    "philips",
    "tcl",
    "hisense",
    "sharp",
    "daikin",
    "midea",
    "carrier",
    "gree",
    "universal",
    "other",
)

PROVIDERS: tuple[str, ...] = ("smartir", "irdb", "lirc", "auto")
DEFAULT_PROVIDER = "auto"

# TODO: Add platforms here as entities are implemented.
PLATFORMS: list[Platform] = []
