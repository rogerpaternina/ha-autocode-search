from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class IRCode:
    """Represent an infrared code independently of its source provider."""

    name: str
    payload: str
    protocol: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    device_type: str | None = None
    supported_models: tuple[str, ...] | None = None
