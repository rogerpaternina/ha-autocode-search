"""Home Assistant services for Autocode Search."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from functools import partial
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from .adapters.home_assistant_remote import HomeAssistantRemoteAdapter
from .const import CONF_PROVIDER, DOMAIN
from .engine import SearchEngine
from .models import SearchSession, SearchStatus
from .providers.memory import InMemoryCodeProvider

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall

    from .coordinator import AutocodeSearchCoordinator

_LOGGER = logging.getLogger(__name__)

SERVICE_START_SEARCH = "start_search"
SERVICE_NEXT_CODE = "next_code"
SERVICE_PREVIOUS_CODE = "previous_code"
SERVICE_FINISH_SEARCH = "finish_search"

_REGISTERED_SERVICES = (
    SERVICE_START_SEARCH,
    SERVICE_NEXT_CODE,
    SERVICE_PREVIOUS_CODE,
    SERVICE_FINISH_SEARCH,
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register Autocode Search services."""
    hass.services.async_register(
        DOMAIN, SERVICE_START_SEARCH, partial(_async_start_search, hass)
    )
    hass.services.async_register(
        DOMAIN, SERVICE_NEXT_CODE, partial(_async_next_code, hass)
    )
    hass.services.async_register(
        DOMAIN, SERVICE_PREVIOUS_CODE, partial(_async_previous_code, hass)
    )
    hass.services.async_register(
        DOMAIN, SERVICE_FINISH_SEARCH, partial(_async_finish_search, hass)
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Remove Autocode Search services."""
    for service in _REGISTERED_SERVICES:
        hass.services.async_remove(DOMAIN, service)


async def _async_start_search(hass: HomeAssistant, call: ServiceCall) -> None:
    """Create and start a new infrared-code search."""
    coordinator = _get_coordinator(hass)
    validation_complete = False

    try:
        entity_id = _required_string(call.data, "entity_id")
        codes = _required_codes(call.data)
        now = datetime.now(UTC)
        _LOGGER.debug("Creating SearchSession")
        session = SearchSession(
            session_id=str(uuid4()),
            device_type=_optional_string(call.data, "device_type"),
            brand=_optional_string(call.data, "brand"),
            command=_optional_string(call.data, "command"),
            current_index=0,
            total_codes=0,
            status=SearchStatus.IDLE,
            started_at=now,
            last_update=now,
        )
        _LOGGER.debug("Creating provider")
        provider = InMemoryCodeProvider(codes)
        _LOGGER.debug("Creating adapter")
        adapter = HomeAssistantRemoteAdapter(hass, entity_id)
        validation_complete = True
        engine = await coordinator.async_start_search(provider, adapter, session)
        _LOGGER.debug("Calling send_current()")
        _LOGGER.debug("Calling remote.send_command()")
        first_code = await engine.send_current()
    except Exception as err:
        if not validation_complete:
            _log_validation_failure(call.data, coordinator)
        _LOGGER.exception("Autocode Search failed")
        raise _service_error("Unable to start the Autocode Search session") from err

    _LOGGER.info(
        "Started Autocode Search session %s for %s", session.session_id, entity_id
    )
    if first_code is None:
        _LOGGER.warning("The search started without an infrared code to send")


async def _async_next_code(hass: HomeAssistant, call: ServiceCall) -> None:
    """Send the next infrared code for the active search."""
    engine = _get_engine(hass)
    try:
        _LOGGER.debug("Calling remote.send_command()")
        code = await engine.next()
    except Exception as err:
        _LOGGER.exception("Autocode Search failed")
        raise _service_error("Unable to send the next infrared code") from err

    if code is None:
        _LOGGER.warning("No next infrared code is available")


async def _async_previous_code(hass: HomeAssistant, call: ServiceCall) -> None:
    """Send the previous infrared code for the active search."""
    engine = _get_engine(hass)
    try:
        _LOGGER.debug("Calling remote.send_command()")
        code = await engine.previous()
    except Exception as err:
        _LOGGER.exception("Autocode Search failed")
        raise _service_error("Unable to send the previous infrared code") from err

    if code is None:
        _LOGGER.warning("No previous infrared code is available")


async def _async_finish_search(hass: HomeAssistant, call: ServiceCall) -> None:
    """Finish the active infrared-code search."""
    engine = _get_engine(hass)
    try:
        await engine.finish()
    except Exception as err:
        _LOGGER.exception("Autocode Search failed")
        raise _service_error("Unable to finish the infrared-code search") from err

    _LOGGER.info("Finished Autocode Search session %s", engine.session.session_id)


def _get_coordinator(hass: HomeAssistant) -> AutocodeSearchCoordinator:
    """Return the configured integration coordinator."""
    from .coordinator import AutocodeSearchCoordinator

    coordinators = (
        value
        for value in hass.data.get(DOMAIN, {}).values()
        if isinstance(value, AutocodeSearchCoordinator)
    )
    coordinator = next(coordinators, None)
    if coordinator is None:
        raise _service_error("Autocode Search is not configured")
    return coordinator


def _get_engine(hass: HomeAssistant) -> SearchEngine:
    """Return the active search engine or raise a service error."""
    engine = _get_coordinator(hass).search_engine
    if engine is None:
        raise _service_error("No active Autocode Search session")
    return engine


def _required_string(data: Mapping[str, Any], key: str) -> str:
    """Return a non-empty string service field or raise a service error."""
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise _service_error(f"Service field '{key}' must be a non-empty string")
    return value


def _optional_string(data: Mapping[str, Any], key: str) -> str:
    """Return an optional string service field, defaulting to an empty string."""
    value = data.get(key, "")
    if not isinstance(value, str):
        raise _service_error(f"Service field '{key}' must be a string")
    return value


def _required_codes(data: Mapping[str, Any]) -> list[str]:
    """Return a non-empty list of infrared-code strings or raise an error."""
    codes = data.get("codes")
    if not isinstance(codes, list) or not codes:
        raise _service_error("Service field 'codes' must be a non-empty list")
    if not all(isinstance(code, str) and code for code in codes):
        raise _service_error("Every code must be a non-empty string")
    return codes


def _log_validation_failure(
    data: Mapping[str, Any], coordinator: AutocodeSearchCoordinator
) -> None:
    """Log the complete service validation context for development diagnostics."""
    codes = data.get("codes")
    number_of_codes = len(codes) if isinstance(codes, list) else None
    _LOGGER.warning(
        "Autocode Search validation failed: entity_id=%r provider=%r "
        "number_of_codes=%r current_session_id=%r",
        data.get("entity_id"),
        coordinator.configuration.get(CONF_PROVIDER),
        number_of_codes,
        coordinator.search_session.session_id,
    )


def _service_error(message: str) -> Exception:
    """Create the Home Assistant error used for invalid service calls."""
    from homeassistant.exceptions import HomeAssistantError

    return HomeAssistantError(message)
