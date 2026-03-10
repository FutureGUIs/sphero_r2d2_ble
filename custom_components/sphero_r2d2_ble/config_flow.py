"""Config flow for Sphero R2-D2 BLE."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from .bluetooth import async_discovered_droids
from .const import DEFAULT_NAME, DOMAIN


class SpheroR2D2BleConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sphero R2-D2 BLE."""

    VERSION = 1
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        discovered = async_discovered_droids(self.hass)

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address.upper())
            self._abort_if_unique_id_configured()
            chosen = next((item for item in discovered if item.address == address), None)
            name = chosen.name if chosen is not None else user_input.get(CONF_NAME, DEFAULT_NAME)
            return self.async_create_entry(
                title=name,
                data={
                    CONF_ADDRESS: address.upper(),
                    CONF_NAME: name,
                },
            )

        if discovered:
            options = {
                item.address: f"{item.name} ({item.address}, RSSI {item.rssi})"
                for item in discovered
            }
            schema = vol.Schema({vol.Required(CONF_ADDRESS): vol.In(options)})
        else:
            errors["base"] = "no_devices_found"
            schema = vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): str,
                    vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                }
            )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_bluetooth(self, discovery_info) -> FlowResult:
        if not discovery_info.connectable:
            return self.async_abort(reason="not_supported")
        await self.async_set_unique_id(discovery_info.address.upper())
        self._abort_if_unique_id_configured()
        self.context["title_placeholders"] = {
            "name": discovery_info.name or discovery_info.address,
        }
        self._async_abort_entries_match({CONF_ADDRESS: discovery_info.address.upper()})
        return self.async_create_entry(
            title=discovery_info.name or discovery_info.address,
            data={
                CONF_ADDRESS: discovery_info.address.upper(),
                CONF_NAME: discovery_info.name or discovery_info.address,
            },
        )
