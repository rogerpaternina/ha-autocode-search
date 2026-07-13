"""Tests for success-record serialization."""

from __future__ import annotations

from datetime import UTC, datetime

from custom_components.autocode_search.memory.models import SuccessRecord
from custom_components.autocode_search.storage.success_repository import (
    STORAGE_VERSION,
    SuccessRepository,
)


def _record(**overrides: object) -> SuccessRecord:
    data = {
        "manufacturer": "LG",
        "model": "OLED55",
        "device_type": "tv",
        "command": "power",
        "provider": "SmartIR",
        "protocol": "NEC",
        "payload": "JgBQAAAB",
        "last_used": datetime(2026, 7, 13, 12, 0, tzinfo=UTC),
        "use_count": 3,
    }
    data.update(overrides)
    return SuccessRecord(**data)  # type: ignore[arg-type]


def test_record_to_dict_serializes_all_fields() -> None:
    """SuccessRepository converts a record into a JSON-friendly dictionary."""
    repository = SuccessRepository()
    record = _record()

    data = repository.record_to_dict(record)

    assert data == {
        "manufacturer": "LG",
        "model": "OLED55",
        "device_type": "tv",
        "command": "power",
        "provider": "SmartIR",
        "protocol": "NEC",
        "payload": "JgBQAAAB",
        "last_used": "2026-07-13T12:00:00+00:00",
        "use_count": 3,
    }


def test_record_from_dict_deserializes_all_fields() -> None:
    """SuccessRepository rebuilds a record from a dictionary."""
    repository = SuccessRepository()

    record = repository.record_from_dict(
        {
            "manufacturer": "LG",
            "model": "OLED55",
            "device_type": "tv",
            "command": "power",
            "provider": "SmartIR",
            "protocol": "NEC",
            "payload": "JgBQAAAB",
            "last_used": "2026-07-13T12:00:00+00:00",
            "use_count": 3,
        }
    )

    assert record == _record()


def test_record_from_dict_rejects_invalid_payload() -> None:
    """Invalid payloads are ignored during deserialization."""
    repository = SuccessRepository()

    record = repository.record_from_dict({"provider": "SmartIR", "use_count": 1})

    assert record is None


def test_to_payload_wraps_records_with_version() -> None:
    """The persisted payload includes the storage version and records list."""
    repository = SuccessRepository()

    payload = repository.to_payload([_record()])

    assert payload["version"] == STORAGE_VERSION
    assert len(payload["records"]) == 1


def test_from_payload_returns_empty_list_for_missing_data() -> None:
    """Missing or empty storage payloads deserialize to an empty list."""
    repository = SuccessRepository()

    assert repository.from_payload(None) == []
    assert repository.from_payload({}) == []
    assert repository.from_payload({"records": "invalid"}) == []
