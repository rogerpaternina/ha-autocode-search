"""Pure Python model for an infrared-code search session."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class SearchStatus(str, Enum):
    """Represent the lifecycle state of a code search."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    FINISHED = "finished"
    CANCELLED = "cancelled"


@dataclass
class SearchSession:
    """Store the state of one device infrared-code search.

    This model deliberately contains no Home Assistant dependencies so it can
    be reused by coordinators, services, adapters, or standalone tests.
    """

    session_id: str
    device_type: str
    brand: str
    command: str
    current_index: int
    total_codes: int
    status: SearchStatus
    started_at: datetime
    last_update: datetime

    def __post_init__(self) -> None:
        """Validate the immutable bounds of the session progress."""
        if self.total_codes < 0:
            raise ValueError("total_codes cannot be negative")
        if not 0 <= self.current_index <= self.total_codes:
            raise ValueError("current_index must be between zero and total_codes")

    def next(self) -> int:
        """Advance to the next code and return the resulting index."""
        if (
            self.status is not SearchStatus.RUNNING
            or self.current_index >= self.total_codes
        ):
            return self.current_index

        self.current_index += 1
        self.last_update = _utcnow()

        if self.current_index >= self.total_codes:
            self.finish()

        return self.current_index

    def previous(self) -> int:
        """Move to the previous code and return the resulting index."""
        if self.current_index <= 0:
            return self.current_index

        self.current_index -= 1
        self.last_update = _utcnow()
        return self.current_index

    def finish(self) -> None:
        """Mark the search as finished."""
        self.current_index = self.total_codes
        self.status = SearchStatus.FINISHED
        self.last_update = _utcnow()

    def cancel(self) -> None:
        """Mark the search as cancelled without changing its progress."""
        self.status = SearchStatus.CANCELLED
        self.last_update = _utcnow()

    def progress(self) -> float:
        """Return completed progress as a fraction between 0.0 and 1.0."""
        if self.total_codes <= 0:
            return 0.0

        return min(self.current_index / self.total_codes, 1.0)


def _utcnow() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)
