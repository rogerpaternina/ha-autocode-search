"""In-memory provider used for explicitly supplied infrared codes."""

from __future__ import annotations

from collections.abc import AsyncIterator

from ..models.ir_code import IRCode
from ..models.search_filter import SearchFilter
from .base import CodeProvider
from .filtering import filter_codes


class InMemoryCodeProvider(CodeProvider):
    """Provide a cursor over a caller-supplied sequence of infrared codes."""

    def __init__(self, codes: list[IRCode] | list[str]) -> None:
        """Initialize the provider with codes in their search order."""
        if not codes:
            self._all_codes: list[IRCode] = []
        elif isinstance(codes[0], str):
            self._all_codes = [
                IRCode(name=code, payload=code) for code in codes
            ]
        else:
            self._all_codes = list(codes)
        self._active_codes: list[IRCode] = []
        self._index = 0
        self._loaded = False

    async def load(self, search_filter: SearchFilter | None = None) -> None:
        """Mark the in-memory codes as ready and apply the optional filter."""
        self._loaded = True
        self._active_codes = filter_codes(self._all_codes, search_filter)
        self.reset()

    async def iter_codes(
        self,
        search_filter: SearchFilter | None = None,
    ) -> AsyncIterator[IRCode]:
        """Yield every in-memory code that matches the optional filter."""
        await self.load(search_filter)
        for code in self._active_codes:
            yield code

    def current(self) -> IRCode | None:
        """Return the code at the current cursor position."""
        if not self._loaded or not self._active_codes:
            return None
        return self._active_codes[self._index]

    def next(self) -> IRCode | None:
        """Advance the cursor and return the next code, if available."""
        if not self._loaded or self._index >= len(self._active_codes) - 1:
            return None
        self._index += 1
        return self.current()

    def previous(self) -> IRCode | None:
        """Move the cursor back and return the previous code, if available."""
        if not self._loaded or self._index == 0:
            return None
        self._index -= 1
        return self.current()

    def count(self) -> int:
        """Return the number of active codes after filtering."""
        return len(self._active_codes)

    def unfiltered_count(self) -> int:
        """Return the number of supplied codes before filtering."""
        return len(self._all_codes)

    def reset(self) -> None:
        """Reset the cursor to the first code."""
        self._index = 0
