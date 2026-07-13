"""Search criteria applied by infrared code providers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SearchFilter:
    """Represent every criterion used to narrow a code search."""

    manufacturer: str | None = None
    model: str | None = None
    device_type: str | None = None
    command: str | None = None

    def is_active(self) -> bool:
        """Return whether at least one filter criterion is set."""
        return any(
            value is not None and value.strip()
            for value in (
                self.manufacturer,
                self.model,
                self.device_type,
                self.command,
            )
        )

    def summary(self) -> str:
        """Return a compact filter label for entity display."""
        if not self.is_active():
            return "No filter"

        parts: list[str] = []
        if self.manufacturer:
            parts.append(self.manufacturer.strip().upper())
        if self.device_type:
            parts.append(self.device_type.strip().upper())
        if self.command:
            parts.append(self.command.strip().upper())
        if self.model:
            parts.append(self.model.strip().upper())
        return " | ".join(parts)

    def description(self) -> str:
        """Return a human-readable description of the active filter."""
        if not self.is_active():
            return "No filter"

        lines: list[str] = []
        if self.manufacturer:
            lines.append(f"Manufacturer: {self.manufacturer.strip().upper()}")
        if self.device_type:
            lines.append(f"Device Type: {self.device_type.strip().upper()}")
        if self.command:
            lines.append(f"Command: {self.command.strip().upper()}")
        if self.model:
            lines.append(f"Model: {self.model.strip().upper()}")
        return "\n".join(lines)
