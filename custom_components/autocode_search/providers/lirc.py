"""LIRC code provider skeleton."""

from __future__ import annotations

from ..models.ir_code import IRCode
from .base import CodeProvider


class LIRCProvider(CodeProvider):
    """Provide a future cursor over LIRC infrared codes."""

    async def load(self) -> None:
        """Load LIRC codes for the requested device and command."""
        # TODO: Load and normalize LIRC code definitions.
        raise NotImplementedError("LIRC provider has not been implemented")

    def current(self) -> IRCode | None:
        """Return the current LIRC code."""
        # TODO: Return the code at the current LIRC cursor position.
        raise NotImplementedError("LIRC provider has not been implemented")

    def next(self) -> IRCode | None:
        """Advance to and return the next LIRC code."""
        # TODO: Advance the LIRC cursor.
        raise NotImplementedError("LIRC provider has not been implemented")

    def previous(self) -> IRCode | None:
        """Move back to and return the previous LIRC code."""
        # TODO: Move the LIRC cursor back one position.
        raise NotImplementedError("LIRC provider has not been implemented")

    def count(self) -> int:
        """Return the number of LIRC codes available."""
        # TODO: Return the number of normalized LIRC codes.
        raise NotImplementedError("LIRC provider has not been implemented")

    def reset(self) -> None:
        """Reset the LIRC cursor."""
        # TODO: Reset the LIRC cursor to its initial position.
        raise NotImplementedError("LIRC provider has not been implemented")
