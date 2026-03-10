"""Config flow for Sphero R2-D2 BLE."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import DEFAULT_NAME, DOMAIN


class SpheroR2D2BleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sphero R2-D2 BLE."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS].upper()
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={
                    CONF_ADDRESS: address,
                    CONF_NAME: user_input[CONF_NAME],
                },
            )

        placeholder = "DF:9A:A3:7C:3F:3F"
        data_schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): selector.TextSelector(),
                vol.Required(CONF_ADDRESS, default=placeholder): selector.TextSelector(),
            }
        )
        return self.async_show_form(step_id="user", data_schema=data_schema, errors=errors)
