"""Config and options flows for Autocode Search."""

from __future__ import annotations

from typing import Any, cast

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    BRANDS,
    CONF_BRAND,
    CONF_DEVICE_TYPE,
    CONF_ENTITY_ID,
    CONF_PROVIDER,
    DEFAULT_PROVIDER,
    DEVICE_TYPES,
    DOMAIN,
    NAME,
    PROVIDERS,
)


class _AutocodeSearchFlowMixin:
    """Share selector schemas and validation between configuration flows."""

    hass: Any

    def _remote_entity_ids(self) -> list[str]:
        """Return sorted entity IDs for all available remote entities."""
        return sorted(state.entity_id for state in self.hass.states.async_all("remote"))

    def _remote_schema(self, default: str | None = None) -> vol.Schema:
        """Build the selector schema for a remote entity."""
        selector = SelectSelector(
            SelectSelectorConfig(
                options=self._remote_entity_ids(),
                mode=SelectSelectorMode.DROPDOWN,
            )
        )
        field = (
            vol.Required(CONF_ENTITY_ID)
            if default is None
            else vol.Required(CONF_ENTITY_ID, default=default)
        )
        return vol.Schema({field: selector})

    @staticmethod
    def _select_schema(
        key: str,
        options: tuple[str, ...],
        translation_key: str,
        default: str | None = None,
    ) -> vol.Schema:
        """Build a translated dropdown selector schema."""
        selector = SelectSelector(
            SelectSelectorConfig(
                options=list(options),
                mode=SelectSelectorMode.DROPDOWN,
                translation_key=translation_key,
            )
        )
        field = (
            vol.Required(key) if default is None else vol.Required(key, default=default)
        )
        return vol.Schema({field: selector})

    def _is_valid_remote(self, entity_id: object) -> bool:
        """Return whether an entity ID belongs to an existing remote entity."""
        return (
            isinstance(entity_id, str)
            and entity_id.startswith("remote.")
            and self.hass.states.get(entity_id) is not None
        )


class AutocodeSearchConfigFlow(
    _AutocodeSearchFlowMixin,
    config_entries.ConfigFlow,
    domain=DOMAIN,  # type: ignore[call-arg]
):
    """Handle the UI configuration flow for Autocode Search."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize values collected across the configuration flow."""
        super().__init__()
        self._data: dict[str, str] = {}

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> AutocodeSearchOptionsFlow:
        """Return the handler used to modify an existing config entry."""
        return AutocodeSearchOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select the Home Assistant remote entity."""
        if not self._remote_entity_ids():
            return self.async_abort(reason="no_remote_entities")

        errors: dict[str, str] = {}
        if user_input is not None:
            entity_id = user_input.get(CONF_ENTITY_ID)

            if not self._is_valid_remote(entity_id):
                errors[CONF_ENTITY_ID] = "invalid_remote"
            else:
                entity_id = cast(str, entity_id)
                self._data[CONF_ENTITY_ID] = entity_id
                await self.async_set_unique_id(entity_id)
                self._abort_if_unique_id_configured()
                return await self.async_step_device_type()

        return self.async_show_form(
            step_id="user",
            data_schema=self._remote_schema(),
            errors=errors,
        )

    async def async_step_device_type(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select the device type to search for."""
        errors: dict[str, str] = {}
        if user_input is not None:
            device_type = user_input.get(CONF_DEVICE_TYPE)
            if device_type not in DEVICE_TYPES:
                errors[CONF_DEVICE_TYPE] = "invalid_device_type"
            else:
                self._data[CONF_DEVICE_TYPE] = device_type
                return await self.async_step_brand()

        return self.async_show_form(
            step_id="device_type",
            data_schema=self._select_schema(
                CONF_DEVICE_TYPE, DEVICE_TYPES, "device_type"
            ),
            errors=errors,
        )

    async def async_step_brand(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select the device brand."""
        errors: dict[str, str] = {}
        if user_input is not None:
            brand = user_input.get(CONF_BRAND)
            if not isinstance(brand, str) or not brand or brand not in BRANDS:
                errors[CONF_BRAND] = "invalid_brand"
            else:
                self._data[CONF_BRAND] = brand
                return await self.async_step_provider()

        return self.async_show_form(
            step_id="brand",
            data_schema=self._select_schema(CONF_BRAND, BRANDS, "brand"),
            errors=errors,
        )

    async def async_step_provider(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select the preferred infrared-code provider."""
        errors: dict[str, str] = {}
        if user_input is not None:
            provider = user_input.get(CONF_PROVIDER)
            if provider not in PROVIDERS:
                errors[CONF_PROVIDER] = "invalid_provider"
            else:
                self._data[CONF_PROVIDER] = provider
                return self.async_create_entry(title=NAME, data=self._data)

        return self.async_show_form(
            step_id="provider",
            data_schema=self._select_schema(
                CONF_PROVIDER, PROVIDERS, "provider", DEFAULT_PROVIDER
            ),
            errors=errors,
        )


class AutocodeSearchOptionsFlow(
    _AutocodeSearchFlowMixin, config_entries.OptionsFlowWithReload
):
    """Handle updates to the Autocode Search configuration."""

    def __init__(self) -> None:
        """Initialize values collected across the options flow."""
        super().__init__()
        self._data: dict[str, str] = {}

    def _current_value(self, key: str) -> str:
        """Return an option value, falling back to the original config entry."""
        value = self.config_entry.options.get(key, self.config_entry.data.get(key, ""))
        return value if isinstance(value, str) else ""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select the Home Assistant remote entity to use."""
        return await self.async_step_remote(user_input)

    async def async_step_remote(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Validate and store the selected remote entity."""
        if not self._remote_entity_ids():
            return self.async_abort(reason="no_remote_entities")

        errors: dict[str, str] = {}
        if user_input is not None:
            entity_id = user_input.get(CONF_ENTITY_ID)

            if not self._is_valid_remote(entity_id):
                errors[CONF_ENTITY_ID] = "invalid_remote"
            else:
                entity_id = cast(str, entity_id)
                self._data[CONF_ENTITY_ID] = entity_id
                return await self.async_step_device_type()

        return self.async_show_form(
            step_id="remote",
            data_schema=self._remote_schema(self._current_value(CONF_ENTITY_ID)),
            errors=errors,
        )

    async def async_step_device_type(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Validate and store the device type."""
        errors: dict[str, str] = {}
        if user_input is not None:
            device_type = user_input.get(CONF_DEVICE_TYPE)
            if device_type not in DEVICE_TYPES:
                errors[CONF_DEVICE_TYPE] = "invalid_device_type"
            else:
                self._data[CONF_DEVICE_TYPE] = device_type
                return await self.async_step_brand()

        return self.async_show_form(
            step_id="device_type",
            data_schema=self._select_schema(
                CONF_DEVICE_TYPE,
                DEVICE_TYPES,
                "device_type",
                self._current_value(CONF_DEVICE_TYPE),
            ),
            errors=errors,
        )

    async def async_step_brand(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Validate and store the device brand."""
        errors: dict[str, str] = {}
        if user_input is not None:
            brand = user_input.get(CONF_BRAND)
            if not isinstance(brand, str) or not brand or brand not in BRANDS:
                errors[CONF_BRAND] = "invalid_brand"
            else:
                self._data[CONF_BRAND] = brand
                return await self.async_step_provider()

        return self.async_show_form(
            step_id="brand",
            data_schema=self._select_schema(
                CONF_BRAND, BRANDS, "brand", self._current_value(CONF_BRAND)
            ),
            errors=errors,
        )

    async def async_step_provider(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Validate and store the preferred code provider."""
        errors: dict[str, str] = {}
        if user_input is not None:
            provider = user_input.get(CONF_PROVIDER)
            if provider not in PROVIDERS:
                errors[CONF_PROVIDER] = "invalid_provider"
            else:
                self._data[CONF_PROVIDER] = provider
                return self.async_create_entry(title="", data=self._data)

        return self.async_show_form(
            step_id="provider",
            data_schema=self._select_schema(
                CONF_PROVIDER,
                PROVIDERS,
                "provider",
                self._current_value(CONF_PROVIDER) or DEFAULT_PROVIDER,
            ),
            errors=errors,
        )
