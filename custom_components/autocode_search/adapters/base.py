"""Abstract interface for infrared hardware adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IRAdapter(ABC):
    """Define the hardware-independent interface used for IR operations."""

    @abstractmethod
    async def send_code(self, code: str) -> None:
        """Send a serialized infrared code through the adapter."""

    @abstractmethod
    async def is_available(self) -> bool:
        """Return whether the underlying IR hardware is available."""

    @abstractmethod
    async def get_device_info(self) -> dict[str, Any]:
        """Return non-sensitive metadata about the underlying IR device."""

