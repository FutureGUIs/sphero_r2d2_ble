"""Select entities for Sphero R2-D2 BLE."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import STANCE_BIPOD, STANCE_TRIPOD
from .entity import R2D2Entity
from .models import RuntimeData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: RuntimeData = entry.runtime_data
    async_add_entities([R2D2StanceSelect(runtime)])


class R2D2StanceSelect(R2D2Entity, SelectEntity):
    _attr_name = "Stance"
    _attr_options = [STANCE_BIPOD, STANCE_TRIPOD]

    def __init__(self, runtime_data: RuntimeData) -> None:
        super().__init__(runtime_data)
        self._attr_unique_id = f"{self.api.address}_stance"

    @property
    def current_option(self) -> str | None:
        return self.coordinator.data.get("stance")

    async def async_select_option(self, option: str) -> None:
        await self.api.async_set_stance(option)
        await self.coordinator.async_request_refresh()
