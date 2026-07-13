"""Sensor entity tests for Autocode Search."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from custom_components.autocode_search.coordinator import AutocodeSearchCoordinator
from custom_components.autocode_search.sensor import (
    AutocodeCodesTestedSensor,
    AutocodeCurrentCommandSensor,
    AutocodeCurrentManufacturerSensor,
    AutocodeCurrentModelSensor,
    AutocodeDuplicatesRemovedSensor,
    AutocodeElapsedTimeSensor,
    AutocodeFilterSummarySensor,
    AutocodeProgressSensor,
    AutocodeProvidersUsedSensor,
    AutocodeTotalCodesSensor,
)


def _create_sensor_environment() -> tuple[AutocodeSearchCoordinator, SimpleNamespace]:
    """Create a coordinator and config entry for sensor tests."""
    hass = SimpleNamespace(data={})
    entry = SimpleNamespace(
        entry_id="entry-1",
        title="Autocode Search",
        data={},
        options={},
    )
    coordinator = AutocodeSearchCoordinator(hass, entry)  # type: ignore[arg-type]
    coordinator.async_set_updated_data = MagicMock()
    coordinator.data = {
        "status": "ready",
        "adapter_available": True,
        "device_info": {"name": "Fake IR Adapter"},
        "session_id": "session-1",
        "search_status": "running",
        "codes_tested": 150,
        "codes_total": 2500,
        "codes_after_filter": 124,
        "filter_description": "Manufacturer: LG\nCommand: POWER",
        "filter_summary": "LG | TV | POWER",
        "progress": 0.06,
        "current_code": "power",
        "current_manufacturer": "LG",
        "current_model": "OLED55",
        "elapsed_time": "00:04:58",
        "search_rate": 0.5,
        "paused": False,
        "cancelled": False,
        "providers_used": ["SmartIR", "IRDB"],
        "providers_completed": ["SmartIR", "IRDB"],
        "duplicates_removed": 54,
    }
    return coordinator, entry


def test_progress_sensor_exposes_percentage() -> None:
    """Progress sensor reflects coordinator data as a percentage."""
    coordinator, entry = _create_sensor_environment()
    sensor = AutocodeProgressSensor(coordinator, entry)  # type: ignore[arg-type]

    assert sensor.native_value == 6.0


def test_codes_tested_and_total_sensors_reflect_coordinator_data() -> None:
    """Codes tested and total sensors read coordinator values."""
    coordinator, entry = _create_sensor_environment()

    assert AutocodeCodesTestedSensor(coordinator, entry).native_value == 150  # type: ignore[arg-type]
    assert AutocodeTotalCodesSensor(coordinator, entry).native_value == 124  # type: ignore[arg-type]


def test_current_metadata_sensors_reflect_coordinator_data() -> None:
    """Current command, manufacturer, and model sensors read coordinator data."""
    coordinator, entry = _create_sensor_environment()

    assert AutocodeCurrentCommandSensor(coordinator, entry).native_value == "power"  # type: ignore[arg-type]
    assert (
        AutocodeCurrentManufacturerSensor(coordinator, entry).native_value == "LG"
    )  # type: ignore[arg-type]
    assert (
        AutocodeCurrentModelSensor(coordinator, entry).native_value == "OLED55"
    )  # type: ignore[arg-type]


def test_elapsed_time_sensor_reflects_coordinator_data() -> None:
    """Elapsed time sensor exposes the formatted coordinator value."""
    coordinator, entry = _create_sensor_environment()

    assert AutocodeElapsedTimeSensor(coordinator, entry).native_value == "00:04:58"  # type: ignore[arg-type]


def test_filter_summary_sensor_reflects_coordinator_data() -> None:
    """Filter summary sensor exposes the active search filter."""
    coordinator, entry = _create_sensor_environment()

    sensor = AutocodeFilterSummarySensor(coordinator, entry)  # type: ignore[arg-type]

    assert sensor.native_value == "LG | TV | POWER"


def test_providers_used_sensor_joins_provider_names() -> None:
    """Providers used sensor exposes a comma-separated provider list."""
    coordinator, entry = _create_sensor_environment()
    sensor = AutocodeProvidersUsedSensor(coordinator, entry)  # type: ignore[arg-type]

    assert sensor.native_value == "SmartIR, IRDB"


def test_providers_used_sensor_without_providers_shows_none() -> None:
    """Providers used sensor falls back to None when no providers ran."""
    coordinator, entry = _create_sensor_environment()
    coordinator.data["providers_used"] = []
    sensor = AutocodeProvidersUsedSensor(coordinator, entry)  # type: ignore[arg-type]

    assert sensor.native_value == "None"


def test_duplicates_removed_sensor_reflects_coordinator_data() -> None:
    """Duplicates removed sensor exposes the deduplication count."""
    coordinator, entry = _create_sensor_environment()
    sensor = AutocodeDuplicatesRemovedSensor(coordinator, entry)  # type: ignore[arg-type]

    assert sensor.native_value == 54
