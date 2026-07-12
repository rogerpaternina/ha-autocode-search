"""Abstract interface for infrared code providers."""

from __future__ import annotations

from abc import ABC, abstractmethod


class CodeProvider(ABC):
    """Define a source-agnostic cursor over infrared codes.

    Search logic can consume this interface without knowing whether codes come
    from a local file, a remote service, or an in-memory data source.
    """

    @abstractmethod
    async def load(self) -> None:
        """Load the codes made available by this provider."""

    @abstractmethod
    def current(self) -> str | None:
        """Return the current code, or ``None`` when there is no current code."""

    @abstractmethod
    def next(self) -> str | None:
        """Advance the cursor and return the next code, if available."""

    @abstractmethod
    def previous(self) -> str | None:
        """Move the cursor back and return the previous code, if available."""

    @abstractmethod
    def count(self) -> int:
        """Return the total number of codes available to the provider."""

    @abstractmethod
    def reset(self) -> None:
        """Reset the provider cursor to its initial position."""

