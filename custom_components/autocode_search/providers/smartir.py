"""SmartIR code provider skeleton."""

from __future__ import annotations

from .base import CodeProvider


class SmartIRProvider(CodeProvider):
    """Provide a future cursor over SmartIR infrared codes."""

    async def load(self) -> None:
        """Load SmartIR codes for the requested device and command."""
        # TODO: Load and normalize SmartIR code definitions.
        raise NotImplementedError("SmartIR provider has not been implemented")

    def current(self) -> str | None:
        """Return the current SmartIR code."""
        # TODO: Return the code at the current SmartIR cursor position.
        raise NotImplementedError("SmartIR provider has not been implemented")

    def next(self) -> str | None:
        """Advance to and return the next SmartIR code."""
        # TODO: Advance the SmartIR cursor.
        raise NotImplementedError("SmartIR provider has not been implemented")

    def previous(self) -> str | None:
        """Move back to and return the previous SmartIR code."""
        # TODO: Move the SmartIR cursor back one position.
        raise NotImplementedError("SmartIR provider has not been implemented")

    def count(self) -> int:
        """Return the number of SmartIR codes available."""
        # TODO: Return the number of normalized SmartIR codes.
        raise NotImplementedError("SmartIR provider has not been implemented")

    def reset(self) -> None:
        """Reset the SmartIR cursor."""
        # TODO: Reset the SmartIR cursor to its initial position.
        raise NotImplementedError("SmartIR provider has not been implemented")

