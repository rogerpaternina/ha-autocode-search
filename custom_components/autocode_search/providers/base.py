"""Abstract interface for infrared code providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from ..models.ir_code import IRCode


class CodeProvider(ABC):
    """Define a source-agnostic cursor over infrared codes.

    Search logic can consume this interface without knowing whether codes come
    from a local file, a remote service, or an in-memory data source.
    """

    @abstractmethod
    async def load(self) -> None:
        """Load the codes made available by this provider."""

    @abstractmethod
    def current(self) -> IRCode | None:
        """Return the current code, or ``None`` when there is no current code."""

    @abstractmethod
    def next(self) -> IRCode | None:
        """Advance the cursor and return the next code, if available."""

    @abstractmethod
    def previous(self) -> IRCode | None:
        """Move the cursor back and return the previous code, if available."""

    @abstractmethod
    def count(self) -> int:
        """Return the total number of codes available to the provider."""

    @abstractmethod
    def reset(self) -> None:
        """Reset the provider cursor to its initial position."""

    async def iter_codes(self) -> AsyncIterator[IRCode]:
        """Yield every available code in provider order."""
        await self.load()
        code = self.current()
        while code is not None:
            yield code
            code = self.next()
