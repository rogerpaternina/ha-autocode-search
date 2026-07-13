"""Helpers for user confirmation of successful infrared codes."""

from __future__ import annotations

import logging

from .memory.success_memory import SuccessMemory, normalize_provider_name
from .models.ir_code import IRCode
from .models.search_filter import SearchFilter
from .providers.base import CodeProvider
from .providers.composite import CompositeCodeProvider
from .providers.ranking import provider_display_name

_LOGGER = logging.getLogger(__name__)


def remember_success(
    success_memory: SuccessMemory,
    search_filter: SearchFilter | None,
    ir_code: IRCode,
    provider_name: str | None,
) -> None:
    """Store a successful code in success memory."""
    success_memory.remember(
        search_filter,
        ir_code,
        provider_name or "unknown",
    )


def resolve_provider_name(
    provider: CodeProvider,
    code: IRCode | None,
    *,
    fallback_provider: str | None = None,
) -> str | None:
    """Return the provider that most likely produced the given code."""
    if code is None:
        return fallback_provider

    if not isinstance(provider, CompositeCodeProvider):
        return provider_display_name(provider)

    for child in provider._providers:
        active_codes = getattr(child, "_active_codes", None)
        if not active_codes:
            continue
        for candidate in active_codes:
            if (
                candidate.payload == code.payload
                and candidate.protocol == code.protocol
            ):
                return provider_display_name(child)

    return fallback_provider


def log_awaiting_confirmation(provider: str | None, command: str | None) -> None:
    """Emit debug logs when a search awaits user confirmation."""
    _LOGGER.debug("Search awaiting user confirmation")
    if provider:
        _LOGGER.debug("Last provider: %s", provider)
    if command:
        _LOGGER.debug("Command: %s", command.upper())


def log_confirmed_success() -> None:
    """Emit debug logs after the user confirms a successful code."""
    _LOGGER.debug("User confirmed successful code")
    _LOGGER.debug("Success stored")
    _LOGGER.debug("Persistence completed")


def log_rejected_result() -> None:
    """Emit debug logs after the user rejects a search result."""
    _LOGGER.debug("User rejected result")


def normalize_manual_provider(provider: str) -> str:
    """Normalize a provider name supplied through a service call."""
    return normalize_provider_name(provider)
