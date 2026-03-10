"""Binary sensors for Sphero R2-D2 BLE."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
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
    async_add_entities([R2D2ConnectedBinarySensor(runtime), R2D2AsleepBinarySensor(runtime)])


class R2D2ConnectedBinarySensor(R2D2Entity, BinarySensorEntity):
    _attr_name = "Connected"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, runtime_data: RuntimeData) -> None:
        super().__init__(runtime_data)
        self._attr_unique_id = f"{self.api.address}_connected"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("connected"))


class R2D2AsleepBinarySensor(R2D2Entity, BinarySensorEntity):
    _attr_name = "Asleep"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, runtime_data: RuntimeData) -> None:
        super().__init__(runtime_data)
        self._attr_unique_id = f"{self.api.address}_asleep"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("asleep"))
