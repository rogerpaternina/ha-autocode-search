"""Data models for successful infrared-code memory."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class SuccessRecord:
    """Represent one previously successful infrared-code attempt."""

    manufacturer: str | None
    model: str | None
    device_type: str | None
    command: str | None
    provider: str
    protocol: str | None
    payload: str
    last_used: datetime
    use_count: int
