"""In-memory provider used for explicitly supplied infrared codes."""

from __future__ import annotations

from ..models.ir_code import IRCode
from .base import CodeProvider


class InMemoryCodeProvider(CodeProvider):
    """Provide a cursor over a caller-supplied sequence of infrared codes."""

    def __init__(self, codes: list[str]) -> None:
        """Initialize the provider with codes in their search order."""
        self._codes = [IRCode(name=code, payload=code) for code in codes]
        self._index = 0
        self._loaded = False

    async def load(self) -> None:
        """Mark the in-memory codes as ready for use."""
        self._loaded = True
        self.reset()

    def current(self) -> IRCode | None:
        """Return the code at the current cursor position."""
        if not self._loaded or not self._codes:
            return None
        return self._codes[self._index]

    def next(self) -> IRCode | None:
        """Advance the cursor and return the next code, if available."""
        if not self._loaded or self._index >= len(self._codes) - 1:
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
        """Return the number of supplied codes."""
        return len(self._codes)

    def reset(self) -> None:
        """Reset the cursor to the first code."""
        self._index = 0
