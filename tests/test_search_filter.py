"""Tests for the SearchFilter model."""

from __future__ import annotations

from custom_components.autocode_search.models.search_filter import SearchFilter


def test_summary_without_filter_returns_no_filter() -> None:
    """An empty filter is reported as having no filter."""
    assert SearchFilter().summary() == "No filter"


def test_summary_formats_active_filter_parts() -> None:
    """Active filters are exposed as a compact summary string."""
    search_filter = SearchFilter(
        manufacturer="lg",
        device_type="tv",
        command="power",
        model="OLED55",
    )

    assert search_filter.summary() == "LG | TV | POWER | OLED55"


def test_description_lists_active_filter_fields() -> None:
    """Active filters produce a multi-line description."""
    search_filter = SearchFilter(manufacturer="lg", command="power")

    assert search_filter.description() == "Manufacturer: LG\nCommand: POWER"
