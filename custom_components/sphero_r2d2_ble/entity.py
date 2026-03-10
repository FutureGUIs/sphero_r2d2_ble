"""Shared entity helpers."""

from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .models import RuntimeData


class R2D2Entity(CoordinatorEntity):
    """Base entity for the integration."""

    _attr_has_entity_name = True

    def __init__(self, runtime_data: RuntimeData) -> None:
        super().__init__(runtime_data.coordinator)
        self.runtime_data = runtime_data
        self.api = runtime_data.api
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.api.address)},
            name=self.api.name,
            manufacturer="Sphero",
            model="Star Wars R2-D2",
            connections={(CONNECTION_BLUETOOTH, self.api.address)},
        )
