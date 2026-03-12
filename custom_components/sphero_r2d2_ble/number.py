"""Number platform for Sphero R2-D2 BLE."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import HEAD_POSITION_MAX, HEAD_POSITION_MIN
from .entity import R2D2Entity
from .models import RuntimeData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: RuntimeData = entry.runtime_data
    async_add_entities([R2D2HeadRotationNumber(runtime)])


class R2D2HeadRotationNumber(R2D2Entity, NumberEntity):
    _attr_name = "Head Rotation"
    _attr_native_min_value = HEAD_POSITION_MIN
    _attr_native_max_value = HEAD_POSITION_MAX
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER
    _attr_native_unit_of_measurement = "deg"

    def __init__(self, runtime_data: RuntimeData) -> None:
        super().__init__(runtime_data)
        self._attr_unique_id = f"{self.api.address}_head_rotation"

    @property
    def native_value(self) -> float:
        return float(self.coordinator.data.get("head_position", 0.0))

    async def async_set_native_value(self, value: float) -> None:
        await self.api.async_set_head_position(value)
        self.coordinator.async_update_local_state(
            head_position=float(value),
            asleep=False,
            connected=True,
        )
        await self.coordinator.async_request_refresh()
