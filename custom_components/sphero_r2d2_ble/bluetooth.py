"""Bluetooth helpers for Sphero droid discovery."""

from __future__ import annotations

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import R2_NAME_PREFIXES
from .models import DiscoveredDroid


def _matches_name(name: str | None) -> bool:
    return bool(name) and any(name.startswith(prefix) for prefix in R2_NAME_PREFIXES)


def discovery_name(info) -> str:
    """Return the best available Bluetooth name for a discovery."""
    return info.name or info.device.name or info.address


def async_discovered_droids(hass: HomeAssistant) -> list[DiscoveredDroid]:
    """Return visible droids from HA's Bluetooth cache."""
    devices: list[DiscoveredDroid] = []
    for info in bluetooth.async_discovered_service_info(hass, connectable=True):
        name = discovery_name(info)
        if not _matches_name(name):
            continue
        devices.append(
            DiscoveredDroid(
                address=info.address,
                name=name,
                rssi=info.rssi,
                connectable=info.connectable,
            )
        )
    devices.sort(key=lambda item: item.rssi if item.rssi is not None else -999, reverse=True)
    return devices
