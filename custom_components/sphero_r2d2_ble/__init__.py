"""The Sphero R2-D2 BLE integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .api import R2D2Api
from .const import (
    CONF_ADDRESS,
    CONF_NAME,
    DOMAIN,
    PLATFORMS,
    SERVICE_PLAY_ANIMATION,
    SERVICE_SET_STANCE,
    STANCE_TO_VALUE,
)
from .coordinator import R2D2Coordinator
from .models import RuntimeData

_LOGGER = logging.getLogger(__name__)

PLAY_ANIMATION_SCHEMA = vol.Schema(
    {
        vol.Required("animation_id"): vol.All(vol.Coerce(int), vol.Range(min=0, max=56)),
        vol.Optional("entity_id"): cv.entity_id,
        vol.Optional("device_id"): cv.string,
    }
)

SET_STANCE_SCHEMA = vol.Schema(
    {
        vol.Required("stance"): vol.In(list(STANCE_TO_VALUE)),
        vol.Optional("entity_id"): cv.entity_id,
        vol.Optional("device_id"): cv.string,
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration."""
    hass.data.setdefault(DOMAIN, {})

    async def _resolve_runtime(call: ServiceCall) -> RuntimeData:
        runtime: RuntimeData | None = None
        if entity_id := call.data.get("entity_id"):
            state = hass.states.get(entity_id)
            if state is None:
                raise HomeAssistantError(f"Entity not found: {entity_id}")
            entry_id = state.attributes.get("config_entry_id")
            if not entry_id:
                raise HomeAssistantError(
                    f"Entity {entity_id} is not associated with a Sphero R2-D2 config entry"
                )
            runtime = hass.data[DOMAIN].get(entry_id)
        elif device_id := call.data.get("device_id"):
            device_registry = dr.async_get(hass)
            device = device_registry.async_get(device_id)
            if device is None:
                raise HomeAssistantError(f"Device not found: {device_id}")
            for entry_id in device.config_entries:
                if entry_id in hass.data[DOMAIN]:
                    runtime = hass.data[DOMAIN][entry_id]
                    break
        else:
            if len(hass.data[DOMAIN]) == 1:
                runtime = next(iter(hass.data[DOMAIN].values()))

        if runtime is None:
            raise HomeAssistantError(
                "Target a specific Sphero R2-D2 device with entity_id or device_id"
            )
        return runtime

    async def handle_play_animation(call: ServiceCall) -> None:
        runtime = await _resolve_runtime(call)
        await runtime.api.async_play_animation(call.data["animation_id"])
        await runtime.coordinator.async_request_refresh()

    async def handle_set_stance(call: ServiceCall) -> None:
        runtime = await _resolve_runtime(call)
        stance = call.data["stance"]
        await runtime.api.async_set_stance(stance)
        runtime.coordinator.async_update_local_state(
            stance=stance,
        )
        await runtime.coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_PLAY_ANIMATION,
        handle_play_animation,
        schema=PLAY_ANIMATION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_STANCE,
        handle_set_stance,
        schema=SET_STANCE_SCHEMA,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    api = R2D2Api(
        hass,
        address=entry.data[CONF_ADDRESS],
        name=entry.data[CONF_NAME],
    )
    coordinator = R2D2Coordinator(hass, _LOGGER, api)
    await coordinator.async_config_entry_first_refresh()

    runtime = RuntimeData(api=api, coordinator=coordinator)
    hass.data[DOMAIN][entry.entry_id] = runtime
    entry.runtime_data = runtime

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        runtime: RuntimeData = hass.data[DOMAIN].pop(entry.entry_id)
        await runtime.api.async_disconnect()
    return unload_ok
