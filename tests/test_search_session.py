"""Tests for the SearchSession model."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from custom_components.autocode_search.models.ir_code import IRCode
from custom_components.autocode_search.models.search_session import (
    InvalidStateTransitionError,
    SearchSession,
    SearchStatus,
)


def _create_session(**overrides: object) -> SearchSession:
    """Create a deterministic search session for tests."""
    now = datetime.now(UTC)
    data = {
        "session_id": "session-1",
        "device_type": "tv",
        "brand": "lg",
        "command": "power",
        "current_index": 0,
        "total_codes": 10,
        "status": SearchStatus.RUNNING,
        "started_at": now,
        "last_update": now,
    }
    data.update(overrides)
    return SearchSession(**data)  # type: ignore[arg-type]


def test_progress_is_calculated_from_codes_tested() -> None:
    """Progress reflects tested codes over the total."""
    session = _create_session(codes_tested=0)
    assert session.progress == 0.0

    session.codes_tested = 5
    assert session.progress == 0.5

    session.codes_tested = 10
    assert session.progress == 1.0


def test_pause_resume_transitions() -> None:
    """A running search can be paused and resumed."""
    session = _create_session()

    session.pause()
    assert session.status is SearchStatus.PAUSED
    assert session.paused is True

    session.resume()
    assert session.status is SearchStatus.RUNNING
    assert session.paused is False


def test_invalid_pause_and_resume_transitions_raise() -> None:
    """Invalid state transitions are rejected."""
    session = _create_session(status=SearchStatus.IDLE)

    with pytest.raises(InvalidStateTransitionError):
        session.pause()

    session.status = SearchStatus.FINISHED
    with pytest.raises(InvalidStateTransitionError):
        session.resume()


def test_cancel_marks_session_as_cancelled() -> None:
    """Cancelling a running search preserves progress and sets finished_at."""
    session = _create_session(codes_tested=3, current_index=2)

    session.cancel()

    assert session.status is SearchStatus.CANCELLED
    assert session.cancelled is True
    assert session.codes_tested == 3
    assert session.current_index == 2
    assert session.finished_at is not None


def test_finish_sets_progress_to_total() -> None:
    """Finishing a search marks every code as tested."""
    session = _create_session(codes_tested=4, current_index=4)

    session.finish()

    assert session.status is SearchStatus.FINISHED
    assert session.codes_tested == 10
    assert session.current_index == 10
    assert session.finished_at is not None


def test_update_current_code_sets_metadata() -> None:
    """Current code metadata is updated from the tested IR code."""
    session = _create_session()
    code = IRCode(
        name="power",
        payload="payload-1",
        manufacturer="LG",
        model="OLED55",
    )

    session.update_current_code(code)

    assert session.current_code == "power"
    assert session.current_manufacturer == "LG"
    assert session.current_model == "OLED55"


def test_format_elapsed_time_uses_started_and_finished_at() -> None:
    """Elapsed time is formatted from timestamps without manual timers."""
    started_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    finished_at = started_at + timedelta(hours=1, minutes=22, seconds=33)
    session = _create_session(
        started_at=started_at,
        finished_at=finished_at,
        status=SearchStatus.FINISHED,
    )

    assert session.format_elapsed_time() == "01:22:33"


def test_search_rate_uses_tested_codes_and_elapsed_time() -> None:
    """Search rate is derived from tested codes and elapsed seconds."""
    started_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    finished_at = started_at + timedelta(seconds=10)
    session = _create_session(
        started_at=started_at,
        finished_at=finished_at,
        codes_tested=10,
        total_codes=10,
        status=SearchStatus.FINISHED,
    )

    assert session.search_rate() == 1.0
