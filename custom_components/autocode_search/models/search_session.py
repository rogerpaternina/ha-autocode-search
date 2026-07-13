"""Pure Python model for an infrared-code search session."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from .ir_code import IRCode


class SearchStatus(StrEnum):
    """Represent the lifecycle state of a code search."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class InvalidStateTransitionError(ValueError):
    """Raised when a session state transition is not allowed."""


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
    started_at: datetime | None
    last_update: datetime
    codes_tested: int = 0
    current_code: str | None = None
    current_manufacturer: str | None = None
    current_model: str | None = None
    finished_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate the immutable bounds of the session progress."""
        if self.total_codes < 0:
            raise ValueError("total_codes cannot be negative")
        if not 0 <= self.current_index <= self.total_codes:
            raise ValueError("current_index must be between zero and total_codes")
        if not 0 <= self.codes_tested <= self.total_codes:
            raise ValueError("codes_tested must be between zero and total_codes")

    @property
    def codes_total(self) -> int:
        """Return the total number of codes in the search."""
        return self.total_codes

    @property
    def progress(self) -> float:
        """Return completed progress as a fraction between 0.0 and 1.0."""
        if self.codes_total <= 0:
            return 0.0

        return min(self.codes_tested / self.codes_total, 1.0)

    @property
    def paused(self) -> bool:
        """Return whether the search is currently paused."""
        return self.status is SearchStatus.PAUSED

    @property
    def cancelled(self) -> bool:
        """Return whether the search was cancelled."""
        return self.status is SearchStatus.CANCELLED

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

    def pause(self) -> None:
        """Pause an active search."""
        if self.status is not SearchStatus.RUNNING:
            raise InvalidStateTransitionError(
                f"Cannot pause a search in state {self.status.value}"
            )

        self.status = SearchStatus.PAUSED
        self.last_update = _utcnow()

    def resume(self) -> None:
        """Resume a paused search."""
        if self.status is not SearchStatus.PAUSED:
            raise InvalidStateTransitionError(
                f"Cannot resume a search in state {self.status.value}"
            )

        self.status = SearchStatus.RUNNING
        self.last_update = _utcnow()

    def finish(self) -> None:
        """Mark the search as finished."""
        if self.status not in (SearchStatus.RUNNING, SearchStatus.PAUSED):
            raise InvalidStateTransitionError(
                f"Cannot finish a search in state {self.status.value}"
            )

        self.current_index = self.total_codes
        self.codes_tested = self.total_codes
        self.status = SearchStatus.FINISHED
        self.finished_at = _utcnow()
        self.last_update = _utcnow()

    def cancel(self) -> None:
        """Mark the search as cancelled without changing its progress."""
        if self.status not in (SearchStatus.RUNNING, SearchStatus.PAUSED):
            raise InvalidStateTransitionError(
                f"Cannot cancel a search in state {self.status.value}"
            )

        self.status = SearchStatus.CANCELLED
        self.finished_at = _utcnow()
        self.last_update = _utcnow()

    def update_current_code(self, code: IRCode) -> None:
        """Update the currently tested code metadata."""
        self.current_code = code.name
        self.current_manufacturer = code.manufacturer
        self.current_model = code.model
        self.last_update = _utcnow()

    def record_forward_progress(self) -> None:
        """Record that another code was tested while moving forward."""
        self.codes_tested = max(self.codes_tested, self.current_index + 1)
        self.last_update = _utcnow()

    def elapsed_seconds(self) -> float:
        """Return elapsed search time in seconds based on timestamps."""
        if self.started_at is None:
            return 0.0

        end_time = self.finished_at or _utcnow()
        return max((end_time - self.started_at).total_seconds(), 0.0)

    def format_elapsed_time(self) -> str:
        """Return elapsed time formatted as HH:MM:SS."""
        total_seconds = int(self.elapsed_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def search_rate(self) -> float | None:
        """Return tested codes per second, or ``None`` when unavailable."""
        elapsed = self.elapsed_seconds()
        if elapsed <= 0 or self.codes_tested <= 0:
            return None

        return self.codes_tested / elapsed


def _utcnow() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(UTC)
