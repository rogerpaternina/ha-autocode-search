"""In-memory store for successful infrared-code attempts."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime

from ..models.ir_code import IRCode
from ..models.search_filter import SearchFilter
from .models import SuccessRecord

_LOGGER = logging.getLogger(__name__)

_PROVIDER_DISPLAY_NAMES = {
    "smartir": "SmartIR",
    "irdb": "IRDB",
    "lirc": "LIRC",
}

_DEFAULT_SUCCESS_MEMORY: SuccessMemory | None = None


class SuccessMemory:
    """Remember successful codes and retrieve relevant matches for future searches.

    The internal list is intentionally simple so a future sprint can replace it
    with Home Assistant Storage without changing the public API.
    """

    def __init__(self) -> None:
        """Initialize an empty in-memory success store."""
        self._records: list[SuccessRecord] = []
        self._persist_callback: Callable[[list[SuccessRecord]], None] | None = None

    def set_persist_callback(
        self,
        callback: Callable[[list[SuccessRecord]], None] | None,
    ) -> None:
        """Register a callback invoked after records change."""
        self._persist_callback = callback

    def load_records(self, records: list[SuccessRecord]) -> None:
        """Replace in-memory records, typically after loading from storage."""
        self._records = list(records)

    def remember(
        self,
        search_filter: SearchFilter | None,
        ir_code: IRCode,
        provider_name: str,
    ) -> SuccessRecord:
        """Record a successful code attempt and return the stored record."""
        now = datetime.now(UTC)
        record = SuccessRecord(
            manufacturer=_field_value(
                search_filter, "manufacturer", ir_code.manufacturer
            ),
            model=_field_value(search_filter, "model", ir_code.model),
            device_type=_field_value(search_filter, "device_type", ir_code.device_type),
            command=_field_value(search_filter, "command", ir_code.name),
            provider=normalize_provider_name(provider_name),
            protocol=ir_code.protocol,
            payload=ir_code.payload,
            last_used=now,
            use_count=1,
        )

        for index, existing in enumerate(self._records):
            if _is_same_record(existing, record):
                updated = SuccessRecord(
                    manufacturer=record.manufacturer,
                    model=record.model,
                    device_type=record.device_type,
                    command=record.command,
                    provider=record.provider,
                    protocol=record.protocol,
                    payload=record.payload,
                    last_used=now,
                    use_count=existing.use_count + 1,
                )
                self._records[index] = updated
                _log_success_recorded(updated)
                self._persist()
                return updated

        self._records.append(record)
        _log_success_recorded(record)
        self._persist()
        return record

    def find(self, search_filter: SearchFilter | None) -> list[SuccessRecord]:
        """Return relevant matches ordered by specificity and usage statistics."""
        if search_filter is None or not search_filter.is_active():
            return []

        matches: list[tuple[int, SuccessRecord]] = []
        for record in self._records:
            tier = _match_tier(record, search_filter)
            if tier is not None:
                matches.append((tier, record))

        matches.sort(
            key=lambda item: (
                item[0],
                -item[1].use_count,
                -item[1].last_used.timestamp(),
            )
        )
        return [record for _, record in matches]

    def clear(self) -> None:
        """Remove every remembered success."""
        self._records.clear()
        self._persist()

    def count(self) -> int:
        """Return how many successes are currently stored."""
        return len(self._records)

    def last_record(self) -> SuccessRecord | None:
        """Return the most recently used success record, if any."""
        if not self._records:
            return None
        return max(self._records, key=lambda record: record.last_used)

    def format_record_summary(self, record: SuccessRecord) -> str:
        """Return a compact human-readable summary for display."""
        parts: list[str] = []
        if record.manufacturer:
            parts.append(record.manufacturer.strip().upper())
        if record.model:
            parts.append(record.model.strip().upper())
        if record.command:
            parts.append(record.command.strip().upper())
        return " ".join(parts) if parts else record.provider

    def _persist(self) -> None:
        if self._persist_callback is not None:
            self._persist_callback(list(self._records))


def reset_default_success_memory() -> SuccessMemory:
    """Replace the shared success-memory instance, primarily for tests."""
    global _DEFAULT_SUCCESS_MEMORY
    _DEFAULT_SUCCESS_MEMORY = SuccessMemory()
    return _DEFAULT_SUCCESS_MEMORY


def default_success_memory() -> SuccessMemory:
    """Return the shared success-memory instance used by the integration."""
    global _DEFAULT_SUCCESS_MEMORY
    if _DEFAULT_SUCCESS_MEMORY is None:
        _DEFAULT_SUCCESS_MEMORY = SuccessMemory()
    return _DEFAULT_SUCCESS_MEMORY


def normalize_provider_name(provider_name: str) -> str:
    """Normalize a provider identifier to its display name."""
    normalized = provider_name.strip()
    mapped = _PROVIDER_DISPLAY_NAMES.get(normalized.casefold())
    if mapped is not None:
        return mapped
    if normalized.casefold().endswith("provider"):
        normalized = normalized[: -len("provider")]
    return normalized[:1].upper() + normalized[1:] if normalized else normalized


def _field_value(
    search_filter: SearchFilter | None,
    field_name: str,
    fallback: str | None,
) -> str | None:
    if search_filter is None:
        return _clean_value(fallback)
    filter_value = getattr(search_filter, field_name)
    if _has_value(filter_value):
        return filter_value.strip()
    return _clean_value(fallback)


def _clean_value(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return value.strip()


def _has_value(value: str | None) -> bool:
    return value is not None and value.strip() != ""


def _normalize(value: str) -> str:
    return value.strip().casefold()


def _values_match(left: str | None, right: str | None) -> bool:
    if left is None or not left.strip():
        return False
    if right is None or not right.strip():
        return False
    return _normalize(left) == _normalize(right)


def _optional_values_match(left: str | None, right: str | None) -> bool:
    left_clean = _clean_value(left)
    right_clean = _clean_value(right)
    if left_clean is None and right_clean is None:
        return True
    if left_clean is None or right_clean is None:
        return False
    return _normalize(left_clean) == _normalize(right_clean)


def _is_same_record(left: SuccessRecord, right: SuccessRecord) -> bool:
    return (
        _optional_values_match(left.manufacturer, right.manufacturer)
        and _optional_values_match(left.model, right.model)
        and _optional_values_match(left.device_type, right.device_type)
        and _optional_values_match(left.command, right.command)
        and left.provider == right.provider
        and left.protocol == right.protocol
        and left.payload == right.payload
    )


def _match_tier(record: SuccessRecord, search_filter: SearchFilter) -> int | None:
    has_manufacturer = _has_value(search_filter.manufacturer)
    has_model = _has_value(search_filter.model)
    has_command = _has_value(search_filter.command)
    has_device_type = _has_value(search_filter.device_type)

    if has_manufacturer and has_model and has_command:
        if (
            _values_match(record.manufacturer, search_filter.manufacturer)
            and _values_match(record.model, search_filter.model)
            and _values_match(record.command, search_filter.command)
        ):
            return 1

    if has_manufacturer and has_model:
        if _values_match(
            record.manufacturer, search_filter.manufacturer
        ) and _values_match(record.model, search_filter.model):
            return 2

    if has_manufacturer and has_device_type:
        if _values_match(
            record.manufacturer, search_filter.manufacturer
        ) and _values_match(record.device_type, search_filter.device_type):
            return 3

    if has_manufacturer:
        if _values_match(record.manufacturer, search_filter.manufacturer):
            return 4

    if has_device_type:
        if _values_match(record.device_type, search_filter.device_type):
            return 5

    return None


def _log_success_recorded(record: SuccessRecord) -> None:
    _LOGGER.debug("Success recorded")
    if record.manufacturer:
        _LOGGER.debug("Manufacturer: %s", record.manufacturer.upper())
    if record.model:
        _LOGGER.debug("Model: %s", record.model.upper())
    if record.command:
        _LOGGER.debug("Command: %s", record.command.upper())
    _LOGGER.debug("Provider: %s", record.provider)
