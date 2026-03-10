"""Number entities for Sphero R2-D2 BLE."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import R2D2Entity
from .models import RuntimeData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: RuntimeData = entry.runtime_data
    async_add_entities([R2D2AnimationNumber(runtime)])


class R2D2AnimationNumber(R2D2Entity, NumberEntity):
    _attr_name = "Animation"
    _attr_native_min_value = 0
    _attr_native_max_value = 56
    _attr_native_step = 1
    _attr_mode = "box"

    def __init__(self, runtime_data: RuntimeData) -> None:
        super().__init__(runtime_data)
        self._attr_unique_id = f"{self.api.address}_animation"
        self._attr_native_value = runtime_data.selected_animation

    async def async_set_native_value(self, value: float) -> None:
        animation_id = int(value)
        self.runtime_data.selected_animation = animation_id
        self._attr_native_value = animation_id
        self.async_write_ha_state()
