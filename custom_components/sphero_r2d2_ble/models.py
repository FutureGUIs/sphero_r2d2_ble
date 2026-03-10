"""Data models for the Sphero R2-D2 BLE integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import R2D2Api


@dataclass
class RuntimeData:
    """Runtime data stored for a config entry."""

    api: R2D2Api
    coordinator: DataUpdateCoordinator[dict[str, Any]]
    selected_animation: int = 0
