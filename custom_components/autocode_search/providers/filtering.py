"""Shared filtering helpers for infrared code providers."""

from __future__ import annotations

from ..models.ir_code import IRCode
from ..models.search_filter import SearchFilter


def normalize(value: str) -> str:
    """Normalize a string for case-insensitive exact comparisons."""
    return value.strip().casefold()


def matches_exact(value: str | None, expected: str | None) -> bool:
    """Return whether two optional strings match exactly after normalization."""
    if expected is None or not expected.strip():
        return True
    if value is None:
        return False
    return normalize(value) == normalize(expected)


def matches_model(code: IRCode, expected_model: str | None) -> bool:
    """Return whether an IR code supports the requested model."""
    if expected_model is None or not expected_model.strip():
        return True

    if code.supported_models:
        return any(
            matches_exact(model, expected_model) for model in code.supported_models
        )

    return matches_exact(code.model, expected_model)


def matches_filter(code: IRCode, search_filter: SearchFilter | None) -> bool:
    """Return whether a code satisfies every active filter criterion."""
    if search_filter is None or not search_filter.is_active():
        return True

    return (
        matches_exact(code.manufacturer, search_filter.manufacturer)
        and matches_model(code, search_filter.model)
        and matches_exact(code.device_type, search_filter.device_type)
        and matches_exact(code.name, search_filter.command)
    )


def filter_codes(
    codes: list[IRCode], search_filter: SearchFilter | None
) -> list[IRCode]:
    """Return the codes that satisfy the requested filter."""
    if search_filter is None or not search_filter.is_active():
        return list(codes)

    return [code for code in codes if matches_filter(code, search_filter)]
