"""Buttons for Sphero R2-D2 BLE."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from homeassistant.components.button import ButtonEntity
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
    async_add_entities(
        [
            R2D2ActionButton(runtime, "Wake", "wake", runtime.api.async_wake),
            R2D2ActionButton(runtime, "Sleep", "sleep", runtime.api.async_sleep),
            R2D2PlayAnimationButton(runtime),
        ]
    )


class R2D2ActionButton(R2D2Entity, ButtonEntity):
    def __init__(
        self,
        runtime_data: RuntimeData,
        name: str,
        key: str,
        action: Callable[[], Awaitable[None]],
    ) -> None:
        super().__init__(runtime_data)
        self._attr_name = name
        self._attr_unique_id = f"{self.api.address}_{key}"
        self._action = action

    async def async_press(self) -> None:
        await self._action()
        await self.coordinator.async_request_refresh()


class R2D2PlayAnimationButton(R2D2Entity, ButtonEntity):
    def __init__(self, runtime_data: RuntimeData) -> None:
        super().__init__(runtime_data)
        self._attr_name = "Play Animation"
        self._attr_unique_id = f"{self.api.address}_play_animation"

    async def async_press(self) -> None:
        await self.api.async_play_animation(self.runtime_data.selected_animation)
        await self.coordinator.async_request_refresh()
