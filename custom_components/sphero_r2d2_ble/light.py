"""Light platform for Sphero R2-D2 BLE."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
)
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
            R2D2LedLight(
                runtime,
                name="Front LED",
                key="front_led",
                data_key="front_led",
                setter=runtime.api.async_set_front_led,
            ),
            R2D2LedLight(
                runtime,
                name="Back LED",
                key="back_led",
                data_key="back_led",
                setter=runtime.api.async_set_back_led,
            ),
            R2D2MonoLight(
                runtime,
                name="Logic Displays",
                key="logic_displays",
                data_key="logic_displays",
                setter=runtime.api.async_set_logic_displays,
            ),
            R2D2MonoLight(
                runtime,
                name="Holo Projector",
                key="holo_projector",
                data_key="holo_projector",
                setter=runtime.api.async_set_holo_projector,
            ),
        ]
    )


class R2D2LedLight(R2D2Entity, LightEntity):
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB

    def __init__(
        self,
        runtime_data: RuntimeData,
        *,
        name: str,
        key: str,
        data_key: str,
        setter: Callable[[tuple[int, int, int]], Awaitable[None]],
    ) -> None:
        super().__init__(runtime_data)
        self._attr_name = name
        self._attr_unique_id = f"{self.api.address}_{key}"
        self._data_key = data_key
        self._setter = setter

    @property
    def rgb_color(self) -> tuple[int, int, int]:
        color = self.coordinator.data.get(self._data_key) or (0, 0, 0)
        return tuple(color)

    @property
    def is_on(self) -> bool:
        return any(self.rgb_color)

    async def async_turn_on(self, **kwargs: Any) -> None:
        rgb = kwargs.get(ATTR_RGB_COLOR, self.rgb_color)
        color = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
        await self._setter(color)
        self.coordinator.async_update_local_state(
            **{
                self._data_key: color,
                "asleep": False,
                "connected": True,
            }
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._setter((0, 0, 0))
        self.coordinator.async_update_local_state(
            **{
                self._data_key: (0, 0, 0),
                "asleep": False,
                "connected": True,
            }
        )
        await self.coordinator.async_request_refresh()


class R2D2MonoLight(R2D2Entity, LightEntity):
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(
        self,
        runtime_data: RuntimeData,
        *,
        name: str,
        key: str,
        data_key: str,
        setter: Callable[[int], Awaitable[None]],
    ) -> None:
        super().__init__(runtime_data)
        self._attr_name = name
        self._attr_unique_id = f"{self.api.address}_{key}"
        self._data_key = data_key
        self._setter = setter

    @property
    def brightness(self) -> int:
        return int(self.coordinator.data.get(self._data_key) or 0)

    @property
    def is_on(self) -> bool:
        return self.brightness > 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        brightness = int(kwargs.get(ATTR_BRIGHTNESS, self.brightness or 255))
        await self._setter(brightness)
        self.coordinator.async_update_local_state(
            **{
                self._data_key: brightness,
                "asleep": False,
                "connected": True,
            }
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._setter(0)
        self.coordinator.async_update_local_state(
            **{
                self._data_key: 0,
                "asleep": False,
                "connected": True,
            }
        )
        await self.coordinator.async_request_refresh()
