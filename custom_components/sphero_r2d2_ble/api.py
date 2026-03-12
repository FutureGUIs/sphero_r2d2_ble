"""BLE API wrapper for the Sphero R2-D2 toy."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any

from bleak import BleakClient
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import (
    AUTH_MESSAGE,
    BATTERY_CHAR_UUID,
    BATTERY_SERVICE_UUID,
    IO_DEVICE_ID,
    IO_SET_ALL_LEDS_WITH_16_BIT_MASK,
    R2_CHAR_AUTH,
    R2_CHAR_CMD,
    R2_CHAR_NOTIFY_1,
    R2_LED_BACK_BLUE,
    R2_LED_BACK_GREEN,
    R2_LED_BACK_RED,
    R2_LED_FRONT_BLUE,
    R2_LED_FRONT_GREEN,
    R2_LED_FRONT_RED,
    R2_LED_HOLO_PROJECTOR,
    R2_LED_LOGIC_DISPLAYS,
    R2_SERVICE_AUTH,
    R2_SERVICE_CMD,
    STANCE_STOP,
    STANCE_TO_VALUE,
)

_LOGGER = logging.getLogger(__name__)

ESCAPE_START = 0x8D
ESCAPE_ESCAPE = 0xAB
ESCAPE_END = 0xD8


class R2D2Error(Exception):
    """Base exception for R2-D2 errors."""


class R2D2NotFoundError(R2D2Error):
    """Raised when the BLE device cannot be found."""


class R2D2Api:
    """Thin command wrapper around the R2-D2 BLE protocol."""

    def __init__(self, hass: HomeAssistant, address: str, name: str) -> None:
        self.hass = hass
        self.address = address.upper()
        self.name = name
        self._client: BleakClient | None = None
        self._lock = asyncio.Lock()
        self._sequence = 0
        self._connected = False
        self._is_asleep = False
        self._last_battery: int | None = None
        self._last_stance: str | None = STANCE_STOP
        self._front_led: tuple[int, int, int] = (0, 0, 0)
        self._back_led: tuple[int, int, int] = (0, 0, 0)
        self._logic_displays = 0
        self._holo_projector = 0

    async def async_disconnect(self) -> None:
        """Disconnect from the robot."""
        async with self._lock:
            await self._async_disconnect_locked()

    async def _async_disconnect_locked(self) -> None:
        client = self._client
        self._client = None
        self._connected = False
        if client and client.is_connected:
            try:
                await client.disconnect()
            except BleakError:
                _LOGGER.debug("Disconnect failed for %s", self.address, exc_info=True)

    def _async_get_ble_device(self):
        return bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )

    async def _ensure_connected_locked(self) -> BleakClient:
        client = self._client
        if client and client.is_connected:
            self._connected = True
            return client

        ble_device = self._async_get_ble_device()
        if ble_device is None:
            raise R2D2NotFoundError(
                f"R2-D2 device {self.address} is not currently available to Home Assistant"
            )

        _LOGGER.debug("Connecting to R2-D2 at %s", self.address)
        client = await establish_connection(
            BleakClient,
            ble_device,
            self.name,
            disconnected_callback=self._disconnected,
            max_attempts=3,
            use_services_cache=True,
        )

        try:
            await self._async_initialize_protocol(client)
        except Exception:
            with contextlib.suppress(Exception):
                await client.disconnect()
            raise

        self._client = client
        self._connected = True
        return client

    async def _async_initialize_protocol(self, client: BleakClient) -> None:
        """Perform the auth/notify handshake copied from the .ino sketch."""
        with contextlib.suppress(Exception):
            await client.start_notify(R2_CHAR_NOTIFY_1, self._notification_handler)

        with contextlib.suppress(Exception):
            await client.write_gatt_char(R2_CHAR_AUTH, AUTH_MESSAGE, response=True)

        with contextlib.suppress(Exception):
            await client.start_notify(R2_CHAR_CMD, self._notification_handler)

        await asyncio.sleep(0.3)
        await self._write_packet_locked(0x13, 0x0D, b"", client=client)

    def _disconnected(self, _client: BleakClient) -> None:
        self._connected = False

    def _notification_handler(self, _handle: int, _data: bytearray) -> None:
        """Ignore notifications for now; we keep them enabled for protocol parity."""

    def _checksum(self, payload: bytes) -> int:
        return (sum(payload) ^ 0xFF) & 0xFF

    def _build_packet(self, device: int, command: int, payload: bytes) -> bytes:
        base = bytearray([0x0A, device & 0xFF, command & 0xFF, self._sequence & 0xFF])
        base.extend(payload)
        base.append(self._checksum(base))

        escaped = bytearray()
        for byte in base:
            if byte == ESCAPE_ESCAPE:
                escaped.extend((ESCAPE_ESCAPE, 0x23))
            elif byte == ESCAPE_START:
                escaped.extend((ESCAPE_ESCAPE, 0x05))
            elif byte == ESCAPE_END:
                escaped.extend((ESCAPE_ESCAPE, 0x50))
            else:
                escaped.append(byte)

        self._sequence = (self._sequence + 1) % 140
        return bytes([ESCAPE_START]) + bytes(escaped) + bytes([ESCAPE_END])

    async def _write_packet_locked(
        self,
        device: int,
        command: int,
        payload: bytes,
        *,
        client: BleakClient | None = None,
    ) -> None:
        current_client = client or await self._ensure_connected_locked()
        packet = self._build_packet(device, command, payload)
        await current_client.write_gatt_char(R2_CHAR_CMD, packet, response=False)
        self._connected = True

    async def async_send_command(self, device: int, command: int, payload: bytes = b"") -> None:
        """Send a raw R2-D2 packet."""
        async with self._lock:
            await self._write_packet_locked(device, command, payload)

    async def async_wake(self) -> None:
        await self.async_send_command(0x13, 0x0D)
        self._is_asleep = False

    async def async_sleep(self) -> None:
        await self.async_send_command(0x13, 0x01)
        self._is_asleep = True

    async def async_play_animation(self, animation_id: int) -> None:
        if not 0 <= animation_id <= 56:
            raise ValueError("animation_id must be between 0 and 56")
        await self.async_send_command(0x17, 0x05, bytes((0x00, animation_id)))
        self._is_asleep = False

    async def async_set_stance(self, stance: str) -> None:
        if stance not in STANCE_TO_VALUE:
            raise ValueError(f"Unsupported stance: {stance}")
        await self.async_send_command(0x17, 0x0D, bytes((STANCE_TO_VALUE[stance],)))
        self._last_stance = stance
        self._is_asleep = False

    async def async_set_front_led(self, rgb: tuple[int, int, int]) -> None:
        await self._async_set_leds(
            (
                (R2_LED_FRONT_RED, rgb[0]),
                (R2_LED_FRONT_GREEN, rgb[1]),
                (R2_LED_FRONT_BLUE, rgb[2]),
            )
        )
        self._front_led = rgb
        self._is_asleep = False

    async def async_set_back_led(self, rgb: tuple[int, int, int]) -> None:
        await self._async_set_leds(
            (
                (R2_LED_BACK_RED, rgb[0]),
                (R2_LED_BACK_GREEN, rgb[1]),
                (R2_LED_BACK_BLUE, rgb[2]),
            )
        )
        self._back_led = rgb
        self._is_asleep = False

    async def async_set_logic_displays(self, brightness: int) -> None:
        level = max(0, min(255, brightness))
        await self._async_set_leds(((R2_LED_LOGIC_DISPLAYS, level),))
        self._logic_displays = level
        self._is_asleep = False

    async def async_set_holo_projector(self, brightness: int) -> None:
        level = max(0, min(255, brightness))
        await self._async_set_leds(((R2_LED_HOLO_PROJECTOR, level),))
        self._holo_projector = level
        self._is_asleep = False

    async def _async_set_leds(self, led_values: tuple[tuple[int, int], ...]) -> None:
        mask = 0
        payload = bytearray()
        for led_index, value in led_values:
            mask |= 1 << led_index
            payload.append(max(0, min(255, value)))
        await self.async_send_command(
            IO_DEVICE_ID,
            IO_SET_ALL_LEDS_WITH_16_BIT_MASK,
            bytes(((mask >> 8) & 0xFF, mask & 0xFF, *payload)),
        )

    async def async_get_status(self) -> dict[str, Any]:
        """Poll current status."""
        async with self._lock:
            battery = None
            try:
                client = await self._ensure_connected_locked()
                raw = await client.read_gatt_char(BATTERY_CHAR_UUID)
                if raw:
                    battery = int(raw[0])
                    self._last_battery = battery
            except Exception:
                _LOGGER.debug("Battery read failed for %s", self.address, exc_info=True)
                battery = self._last_battery

            asleep = self.is_asleep
            return {
                "connected": self._connected and bool(self._client and self._client.is_connected),
                "battery": battery,
                "asleep": asleep,
                "stance": self._last_stance,
                "front_led": self._front_led,
                "back_led": self._back_led,
                "logic_displays": self._logic_displays,
                "holo_projector": self._holo_projector,
            }

    @property
    def is_asleep(self) -> bool:
        return self._is_asleep
