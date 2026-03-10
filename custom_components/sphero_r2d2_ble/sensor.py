"""Sensor platform for Sphero R2-D2 BLE."""

from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, PERCENTAGE
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
    async_add_entities([R2D2BatterySensor(runtime)])


class R2D2BatterySensor(R2D2Entity, SensorEntity):
    _attr_name = "Battery"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_unique_id = None

    def __init__(self, runtime_data: RuntimeData) -> None:
        super().__init__(runtime_data)
        self._attr_unique_id = f"{self.api.address}_battery"

    @property
    def native_value(self):
        return self.coordinator.data.get("battery")
