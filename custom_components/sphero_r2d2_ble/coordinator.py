"""Coordinator for Sphero R2-D2 BLE."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import R2D2Api, R2D2Error
from .const import UPDATE_INTERVAL


class R2D2Coordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate periodic status updates."""

    def __init__(self, hass, logger, api: R2D2Api) -> None:
        super().__init__(
            hass,
            logger,
            name=f"{api.name} status",
            update_interval=UPDATE_INTERVAL,
        )
        self.api = api
        api.set_state_callback(self._async_api_state_changed)

    def _async_api_state_changed(self) -> None:
        """Publish transport changes without scheduling a reconnect or poll."""
        self.async_update_local_state(**self.api.status_snapshot())

    async def async_startup(self) -> None:
        """Attempt a wake in the background while offline entities stay loaded."""
        self.async_set_updated_data(await self.api.async_startup())

    def async_update_local_state(self, **changes: Any) -> None:
        """Push known state changes to entities without waiting for a poll."""
        current = dict(self.data) if self.data else {}
        current.update(changes)
        # Entity actions must not overwrite a concurrent disconnect with an
        # optimistic connected=True after a successful GATT write.
        current["connected"] = self.api.is_connected
        self.async_set_updated_data(current)

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.api.async_get_status()
        except R2D2Error as err:
            raise UpdateFailed(str(err)) from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected update failure: {err}") from err
