from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class IRCode:
    """Representa un código IR independiente del proveedor."""

    payload: str

    encoding: str

    source: str

    brand: str

    command: str

    model: str | None = None

    protocol: str | None = None
