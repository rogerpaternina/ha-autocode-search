"""Basic service registration tests for Autocode Search."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from custom_components.autocode_search import services


def test_setup_registers_search_services() -> None:
    """All Autocode Search services are registered with Home Assistant."""
    hass = MagicMock()

    asyncio.run(services.async_setup_services(hass))

    assert hass.services.async_register.call_count == 4
    registered_services = {
        call.args[1] for call in hass.services.async_register.call_args_list
    }
    assert registered_services == {
        services.SERVICE_START_SEARCH,
        services.SERVICE_NEXT_CODE,
        services.SERVICE_PREVIOUS_CODE,
        services.SERVICE_FINISH_SEARCH,
    }


def test_unload_removes_search_services() -> None:
    """All Autocode Search services are removed when the integration unloads."""
    hass = MagicMock()

    asyncio.run(services.async_unload_services(hass))

    assert hass.services.async_remove.call_count == 4
