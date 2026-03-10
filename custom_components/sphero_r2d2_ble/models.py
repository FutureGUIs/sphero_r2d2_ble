"""Data models for the Sphero R2-D2 BLE integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .api import R2D2Api

if TYPE_CHECKING:
    from .coordinator import R2D2Coordinator


@dataclass
class RuntimeData:
    """Runtime data stored for a config entry."""

    api: R2D2Api
    coordinator: R2D2Coordinator
    selected_animation: int = 0


@dataclass(slots=True, frozen=True)
class DiscoveredDroid:
    """A droid discovered through Home Assistant Bluetooth."""

    address: str
    name: str
    rssi: int | None
    connectable: bool
