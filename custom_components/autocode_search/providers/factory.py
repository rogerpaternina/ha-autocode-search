from __future__ import annotations

from typing import TYPE_CHECKING

from .base import CodeProvider
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
    ) -> CodeProvider:
        """Crear proveedor por nombre."""

        try:
            provider_class = cls._PROVIDERS[provider_name.lower()]
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
