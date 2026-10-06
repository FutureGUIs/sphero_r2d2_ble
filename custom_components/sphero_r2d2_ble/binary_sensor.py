"""Binary sensors for Sphero R2-D2 BLE."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
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
    async_add_entities([
        R2D2ConnectedBinarySensor(runtime), R2D2AsleepBinarySensor(runtime),
        R2D2NearbyBinarySensor(runtime),
    ])


class R2D2ConnectedBinarySensor(R2D2Entity, BinarySensorEntity):
    _attr_name = "Connected"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, runtime_data: RuntimeData) -> None:
        super().__init__(runtime_data)
        self._attr_unique_id = f"{self.api.address}_connected"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("connected"))

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        return {key: data.get(key) for key in (
            "connection_status", "last_communication", "last_error",
        )}


class R2D2NearbyBinarySensor(R2D2Entity, BinarySensorEntity):
    """Advertisement presence, independent of an active BLE session."""

    _attr_name = "Nearby"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, runtime_data: RuntimeData) -> None:
        super().__init__(runtime_data)
        self._attr_unique_id = f"{self.api.address}_nearby"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("nearby"))

    @property
    def extra_state_attributes(self):
        return {"last_seen": self.coordinator.data.get("last_seen")}


class R2D2AsleepBinarySensor(R2D2Entity, BinarySensorEntity):
    _attr_name = "Asleep"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, runtime_data: RuntimeData) -> None:
        super().__init__(runtime_data)
        self._attr_unique_id = f"{self.api.address}_asleep"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("asleep"))

    @property
    def extra_state_attributes(self):
        return {"state_source": self.coordinator.data.get("sleep_state_source")}
