"""Composite provider that chains multiple code providers transparently."""

from __future__ import annotations

import logging

from ..models.ir_code import IRCode
from ..models.search_filter import SearchFilter
from .base import CodeProvider
from .ranking import ProviderRanking, provider_display_name

_LOGGER = logging.getLogger(__name__)


class CompositeCodeProvider(CodeProvider):
    """Deliver codes from an ordered list of providers as a single stream.

    The consumer never learns how many providers exist or which one produced
    each code. Providers are iterated in priority order and duplicate codes
    (same payload and protocol) are delivered only once.
    """

    def __init__(
        self,
        providers: list[CodeProvider],
        ranking: ProviderRanking | None = None,
    ) -> None:
        """Initialize the composite with providers in priority order."""
        self._providers = list(providers)
        self._ranking = ranking or ProviderRanking()
        self._active_codes: list[IRCode] = []
        self._index = 0
        self._loaded = False
        self.providers_used: list[str] = []
        self.providers_completed: list[str] = []
        self.duplicates_removed: int = 0
        self.provider_order: list[str] = []
        self.provider_ranking_reason: str = ""

    async def load(self, search_filter: SearchFilter | None = None) -> None:
        """Load every provider in order and build the deduplicated stream."""
        _LOGGER.debug("Composite provider started")
        self._active_codes = []
        self.providers_used = []
        self.providers_completed = []
        self.duplicates_removed = 0
        seen: set[tuple[str, str | None]] = set()

        ranking_result = self._ranking.rank(search_filter, self._providers)
        ordered_providers = ranking_result.providers
        self.provider_order = [
            provider_display_name(provider) for provider in ordered_providers
        ]
        self.provider_ranking_reason = ranking_result.reason

        for provider in ordered_providers:
            provider_name = provider_display_name(provider)
            _LOGGER.debug("Provider %s", provider_name)
            self.providers_used.append(provider_name)

            loaded_codes = 0
            removed_duplicates = 0
            async for code in provider.iter_codes(search_filter):
                loaded_codes += 1
                key = (code.payload, code.protocol)
                if key in seen:
                    removed_duplicates += 1
                    continue
                seen.add(key)
                self._active_codes.append(code)

            self.duplicates_removed += removed_duplicates
            _LOGGER.debug("Loaded %d codes", loaded_codes)
            _LOGGER.debug("Duplicates removed: %d", removed_duplicates)
            self.providers_completed.append(provider_name)
            _LOGGER.debug("Provider completed")

        self._loaded = True
        _LOGGER.debug("Composite completed")
        self.reset()

    def current(self) -> IRCode | None:
        """Return the code at the current composite cursor position."""
        if not self._loaded or not self._active_codes:
            return None
        return self._active_codes[self._index]

    def next(self) -> IRCode | None:
        """Advance the composite cursor and return the next code."""
        if not self._loaded or self._index >= len(self._active_codes) - 1:
            return None
        self._index += 1
        return self.current()

    def previous(self) -> IRCode | None:
        """Move the composite cursor back and return the previous code."""
        if not self._loaded or self._index == 0:
            return None
        self._index -= 1
        return self.current()

    def count(self) -> int:
        """Return the number of deduplicated codes across all providers."""
        return len(self._active_codes)

    def unfiltered_count(self) -> int:
        """Return the raw code total across every provider, with duplicates."""
        return sum(provider.unfiltered_count() for provider in self._providers)

    def reset(self) -> None:
        """Reset the composite cursor and every underlying provider."""
        self._index = 0
        for provider in self._providers:
            provider.reset()
