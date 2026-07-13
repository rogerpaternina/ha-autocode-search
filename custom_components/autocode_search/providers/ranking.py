"""Provider priority ranking based on search filter criteria."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from ..models.search_filter import SearchFilter
from .base import CodeProvider

_LOGGER = logging.getLogger(__name__)

_CLIMATE_DEVICE_TYPES = frozenset({"climate", "air_conditioner"})


@dataclass(slots=True)
class RankingResult:
    """Ordered providers and the reason for that ordering."""

    providers: list[CodeProvider]
    reason: str


class RankingRule(Protocol):
    """Match a filter and assign relative priorities to known providers."""

    def matches(self, search_filter: SearchFilter) -> bool:
        """Return whether this rule applies to the given filter."""

    def reason(self) -> str:
        """Return a short human-readable explanation for this rule."""

    def priorities(self) -> dict[str, int]:
        """Return provider display names mapped to priority (lower is first)."""


@dataclass(frozen=True, slots=True)
class _ModelSpecifiedRule:
    """Prioritize IRDB when a device model is known."""

    def matches(self, search_filter: SearchFilter) -> bool:
        return _has_value(search_filter.model)

    def reason(self) -> str:
        return "Model specified"

    def priorities(self) -> dict[str, int]:
        return {"IRDB": 0, "SmartIR": 1}


@dataclass(frozen=True, slots=True)
class _ClimateDeviceRule:
    """Prioritize SmartIR for climate devices."""

    def matches(self, search_filter: SearchFilter) -> bool:
        device_type = search_filter.device_type
        if device_type is None or not device_type.strip():
            return False
        return device_type.strip().lower() in _CLIMATE_DEVICE_TYPES

    def reason(self) -> str:
        return "Climate device"

    def priorities(self) -> dict[str, int]:
        return {"SmartIR": 0, "IRDB": 1}


@dataclass(frozen=True, slots=True)
class _DefaultRule:
    """Fallback ordering when no more specific rule matches."""

    def matches(self, search_filter: SearchFilter) -> bool:
        return True

    def reason(self) -> str:
        return "Default order"

    def priorities(self) -> dict[str, int]:
        return {"SmartIR": 0, "IRDB": 1}


_RANKING_RULES: tuple[RankingRule, ...] = (
    _ModelSpecifiedRule(),
    _ClimateDeviceRule(),
    _DefaultRule(),
)


class ProviderRanking:
    """Decide provider consultation order from a search filter.

    Designed for future extension with weights, historical statistics,
    user configuration, and machine-learning strategies without changing
    the composite provider contract.
    """

    def __init__(self, rules: tuple[RankingRule, ...] | None = None) -> None:
        """Initialize the ranking engine with an ordered rule chain."""
        self._rules = rules if rules is not None else _RANKING_RULES

    def rank(
        self,
        search_filter: SearchFilter | None,
        providers: list[CodeProvider],
    ) -> RankingResult:
        """Return providers sorted by priority without executing searches."""
        ordered = list(providers)

        if search_filter is None or not search_filter.is_active():
            result = RankingResult(ordered, "Default order")
            self._log_ranking(search_filter, result)
            return result

        rule = self._select_rule(search_filter)
        ordered = self._sort_providers(providers, rule.priorities())
        result = RankingResult(ordered, rule.reason())
        self._log_ranking(search_filter, result)
        return result

    def _select_rule(self, search_filter: SearchFilter) -> RankingRule:
        for rule in self._rules:
            if rule.matches(search_filter):
                return rule
        return _DefaultRule()

    def _sort_providers(
        self,
        providers: list[CodeProvider],
        priorities: dict[str, int],
    ) -> list[CodeProvider]:
        return sorted(
            providers,
            key=lambda provider: (
                priorities.get(
                    provider_display_name(provider),
                    len(priorities),
                ),
                providers.index(provider),
            ),
        )

    def _log_ranking(
        self,
        search_filter: SearchFilter | None,
        result: RankingResult,
    ) -> None:
        _LOGGER.debug("Provider ranking started")
        if search_filter is not None and search_filter.is_active():
            if search_filter.manufacturer:
                _LOGGER.debug("manufacturer=%s", search_filter.manufacturer)
            if search_filter.model:
                _LOGGER.debug("model=%s", search_filter.model)
            if search_filter.device_type:
                _LOGGER.debug("device_type=%s", search_filter.device_type)
            if search_filter.command:
                _LOGGER.debug("command=%s", search_filter.command)
        _LOGGER.debug("Ranking result")
        for index, provider in enumerate(result.providers):
            if index > 0:
                _LOGGER.debug("↓")
            _LOGGER.debug("%s", provider_display_name(provider))
        _LOGGER.debug("Reason:")
        _LOGGER.debug("%s", result.reason)


def provider_display_name(provider: CodeProvider) -> str:
    """Return a short display name for a provider instance."""
    name = type(provider).__name__
    for suffix in ("CodeProvider", "Provider"):
        if name.endswith(suffix) and len(name) > len(suffix):
            return name[: -len(suffix)]
    return name


def _has_value(value: str | None) -> bool:
    return value is not None and value.strip() != ""
