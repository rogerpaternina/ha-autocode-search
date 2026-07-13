from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from .base import CodeProvider
from .composite import CompositeCodeProvider
from .irdb import IRDBProvider
from .lirc import LIRCProvider
from .memory import InMemoryCodeProvider
from .smartir import SmartIRProvider

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

type ProviderClass = (
    type[SmartIRProvider]
    | type[IRDBProvider]
    | type[LIRCProvider]
    | type[InMemoryCodeProvider]
)

# Priority order used when the composite provider is requested. Extend this
# list (e.g. with "lirc") to include future providers without touching the
# SearchEngine or the composite implementation.
DEFAULT_COMPOSITE_ORDER: tuple[str, ...] = ("smartir", "irdb")


class ProviderFactory:
    """Factory para crear proveedores IR."""

    _PROVIDERS: dict[str, ProviderClass] = {
        "smartir": SmartIRProvider,
        "irdb": IRDBProvider,
        "lirc": LIRCProvider,
        "memory": InMemoryCodeProvider,
    }

    @classmethod
    def create(
        cls,
        provider_name: str,
        hass: HomeAssistant | None = None,
        *,
        codes: list[str] | None = None,
        composite_order: Sequence[str] | None = None,
    ) -> CodeProvider:
        """Crear proveedor por nombre."""
        name = provider_name.lower()

        if name == "composite":
            order = composite_order or DEFAULT_COMPOSITE_ORDER
            return CompositeCodeProvider(
                [cls.create(member, hass, codes=codes) for member in order]
            )

        try:
            provider_class = cls._PROVIDERS[name]
        except KeyError as err:
            raise ValueError(f"Unknown provider: {provider_name}") from err

        if provider_class is InMemoryCodeProvider:
            if not codes:
                raise ValueError("Memory provider requires explicit codes")
            return InMemoryCodeProvider(codes)

        if provider_class is SmartIRProvider:
            return SmartIRProvider(hass)

        if provider_class is IRDBProvider:
            return IRDBProvider(hass)

        return LIRCProvider()
