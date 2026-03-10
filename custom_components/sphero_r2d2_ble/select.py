"""Select entities for Sphero R2-D2 BLE."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ANIMATION_CHOICES,
    ANIMATION_ID_TO_OPTION,
    ANIMATION_OPTIONS,
    STANCE_BIPOD,
    STANCE_TRIPOD,
)
from .entity import R2D2Entity
from .models import RuntimeData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: RuntimeData = entry.runtime_data
    async_add_entities([R2D2StanceSelect(runtime), R2D2AnimationSelect(runtime)])


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
        self.coordinator.async_update_local_state(
            stance=option,
        )
        await self.coordinator.async_request_refresh()


class R2D2AnimationSelect(R2D2Entity, SelectEntity):
    _attr_name = "Animation"
    _attr_options = ANIMATION_OPTIONS

    def __init__(self, runtime_data: RuntimeData) -> None:
        super().__init__(runtime_data)
        self._attr_unique_id = f"{self.api.address}_animation"

    @property
    def current_option(self) -> str | None:
        return ANIMATION_ID_TO_OPTION.get(self.runtime_data.selected_animation)

    async def async_select_option(self, option: str) -> None:
        self.runtime_data.selected_animation = ANIMATION_CHOICES[option]
        self.async_write_ha_state()
