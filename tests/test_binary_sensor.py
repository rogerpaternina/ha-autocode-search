"""Binary sensor entity tests for Autocode Search."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from custom_components.autocode_search.binary_sensor import AutocodeRunningBinarySensor
from custom_components.autocode_search.coordinator import AutocodeSearchCoordinator


def _create_binary_sensor(search_status: str) -> AutocodeRunningBinarySensor:
    """Create a running binary sensor with the given search status."""
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
        "search_status": search_status,
        "codes_tested": 0,
        "codes_total": 0,
        "progress": 0.0,
        "current_code": None,
        "current_manufacturer": None,
        "current_model": None,
        "elapsed_time": "00:00:00",
        "search_rate": None,
        "paused": search_status == "paused",
        "cancelled": search_status == "cancelled",
    }
    return AutocodeRunningBinarySensor(coordinator, entry)  # type: ignore[arg-type]


def test_running_binary_sensor_is_on_only_when_running() -> None:
    """The running binary sensor is on only for active searches."""
    assert _create_binary_sensor("running").is_on is True
    assert _create_binary_sensor("idle").is_on is False
    assert _create_binary_sensor("paused").is_on is False
    assert _create_binary_sensor("finished").is_on is False
    assert _create_binary_sensor("cancelled").is_on is False
