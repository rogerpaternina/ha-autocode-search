"""Tests for provider filtering helpers."""

from __future__ import annotations

from custom_components.autocode_search.models.ir_code import IRCode
from custom_components.autocode_search.models.search_filter import SearchFilter
from custom_components.autocode_search.providers.filtering import (
    matches_exact,
    matches_filter,
)


def _code(**overrides: object) -> IRCode:
    data = {
        "name": "power",
        "payload": "payload",
        "manufacturer": "LG",
        "model": "OLED55",
        "device_type": "tv",
        "supported_models": ("OLED55", "OLED65"),
    }
    data.update(overrides)
    return IRCode(**data)  # type: ignore[arg-type]


def test_matches_exact_is_case_insensitive_and_trims_spaces() -> None:
    """Exact matches ignore case and surrounding whitespace."""
    assert matches_exact(" LG ", "lg") is True
    assert matches_exact("Lg", "LG") is True
    assert matches_exact("Sony", "LG") is False


def test_matches_filter_by_manufacturer_device_type_and_command() -> None:
    """Multiple active criteria must all match."""
    search_filter = SearchFilter(
        manufacturer="lg",
        device_type="tv",
        command="power",
    )

    assert matches_filter(_code(), search_filter) is True
    assert matches_filter(_code(manufacturer="Samsung"), search_filter) is False
    assert matches_filter(_code(device_type="fan"), search_filter) is False
    assert matches_filter(_code(name="volume_up"), search_filter) is False


def test_matches_filter_by_supported_models() -> None:
    """Model filters match any supported SmartIR model."""
    search_filter = SearchFilter(model="oled65")

    assert matches_filter(_code(), search_filter) is True
    assert matches_filter(_code(supported_models=("ABC123",)), search_filter) is False
