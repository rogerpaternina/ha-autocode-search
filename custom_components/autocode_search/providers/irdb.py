"""IRDB code provider skeleton."""

from __future__ import annotations

from .base import CodeProvider


class IRDBProvider(CodeProvider):
    """Provide a future cursor over IRDB infrared codes."""

    async def load(self) -> None:
        """Load IRDB codes for the requested device and command."""
        # TODO: Load and normalize IRDB code definitions.
        raise NotImplementedError("IRDB provider has not been implemented")

    def current(self) -> str | None:
        """Return the current IRDB code."""
        # TODO: Return the code at the current IRDB cursor position.
        raise NotImplementedError("IRDB provider has not been implemented")

    def next(self) -> str | None:
        """Advance to and return the next IRDB code."""
        # TODO: Advance the IRDB cursor.
        raise NotImplementedError("IRDB provider has not been implemented")

    def previous(self) -> str | None:
        """Move back to and return the previous IRDB code."""
        # TODO: Move the IRDB cursor back one position.
        raise NotImplementedError("IRDB provider has not been implemented")

    def count(self) -> int:
        """Return the number of IRDB codes available."""
        # TODO: Return the number of normalized IRDB codes.
        raise NotImplementedError("IRDB provider has not been implemented")

    def reset(self) -> None:
        """Reset the IRDB cursor."""
        # TODO: Reset the IRDB cursor to its initial position.
        raise NotImplementedError("IRDB provider has not been implemented")

