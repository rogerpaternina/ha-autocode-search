"""Config flow for Autocode Search."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, NAME


class AutocodeSearchConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Autocode Search."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial setup step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            # TODO: Collect connection or search-provider settings if required.
            return self.async_create_entry(title=NAME, data={})

        return self.async_show_form(step_id="user", data_schema=None)

