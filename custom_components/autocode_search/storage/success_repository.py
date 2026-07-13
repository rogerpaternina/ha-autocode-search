"""Translate success records to and from storage payloads."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..memory.models import SuccessRecord

STORAGE_VERSION = 1


class SuccessRepository:
    """Convert between SuccessRecord objects and storage dictionaries."""

    def to_payload(self, records: list[SuccessRecord]) -> dict[str, Any]:
        """Serialize records into the persisted storage payload."""
        return {
            "version": STORAGE_VERSION,
            "records": [self.record_to_dict(record) for record in records],
        }

    def from_payload(self, payload: dict[str, Any] | None) -> list[SuccessRecord]:
        """Deserialize records from a storage payload."""
        if not payload:
            return []

        raw_records = payload.get("records")
        if not isinstance(raw_records, list):
            return []

        return [
            record
            for item in raw_records
            if isinstance(item, dict)
            for record in [self.record_from_dict(item)]
            if record is not None
        ]

    def record_to_dict(self, record: SuccessRecord) -> dict[str, Any]:
        """Serialize one success record to a dictionary."""
        return {
            "manufacturer": record.manufacturer,
            "model": record.model,
            "device_type": record.device_type,
            "command": record.command,
            "provider": record.provider,
            "protocol": record.protocol,
            "payload": record.payload,
            "last_used": record.last_used.isoformat(),
            "use_count": record.use_count,
        }

    def record_from_dict(self, data: dict[str, Any]) -> SuccessRecord | None:
        """Deserialize one success record from a dictionary."""
        payload = data.get("payload")
        provider = data.get("provider")
        last_used_raw = data.get("last_used")
        use_count = data.get("use_count")

        if not isinstance(payload, str) or not payload:
            return None
        if not isinstance(provider, str) or not provider:
            return None
        if not isinstance(last_used_raw, str) or not last_used_raw:
            return None
        if not isinstance(use_count, int) or use_count < 1:
            return None

        try:
            last_used = datetime.fromisoformat(last_used_raw)
        except ValueError:
            return None
        if last_used.tzinfo is None:
            last_used = last_used.replace(tzinfo=UTC)

        return SuccessRecord(
            manufacturer=_optional_string(data.get("manufacturer")),
            model=_optional_string(data.get("model")),
            device_type=_optional_string(data.get("device_type")),
            command=_optional_string(data.get("command")),
            provider=provider,
            protocol=_optional_string(data.get("protocol")),
            payload=payload,
            last_used=last_used,
            use_count=use_count,
        )


def _optional_string(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()
