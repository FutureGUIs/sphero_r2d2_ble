"""BLE API wrapper for the Sphero R2-D2 toy."""

from __future__ import annotations

import asyncio
import logging
import struct
from collections.abc import Callable
from datetime import datetime, timezone
from time import monotonic
from typing import Any

from bleak import BleakClient
from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .const import (
    ANIMATRONIC_DEVICE_ID,
    ANIMATRONIC_SET_HEAD_POSITION,
    AUTH_MESSAGE,
    BATTERY_CHAR_UUID,
    HEAD_POSITION_MAX,
    HEAD_POSITION_MIN,
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
        self._head_position = 0.0
        self._state_callback: Callable[[], None] | None = None
        self._connecting = False
        self._nearby = False
        self._last_seen: datetime | None = None
        self._last_communication: datetime | None = None
        self._battery_updated_at: datetime | None = None
        self._last_error: str | None = None
        self._retry_delay = 60.0
        self._next_retry = 0.0
        self._stopped = False
        self._startup_wake_pending = False
        self._notification_buffers: dict[str, bytearray] = {}
        self._sleep_state_source = "unknown"

    def set_state_callback(self, callback: Callable[[], None] | None) -> None:
        """Subscribe to state changes on Home Assistant's event loop."""
        self._state_callback = callback

    def _publish_state(self) -> None:
        if self._state_callback is not None:
            self._state_callback()

    def async_update_presence(self, nearby: bool) -> None:
        """Track advertisements separately from the active BLE connection."""
        changed = self._nearby != nearby
        self._nearby = nearby
        if nearby:
            self._last_seen = datetime.now(timezone.utc)
        if changed:
            self._publish_state()

    @property
    def is_connected(self) -> bool:
        return self._connected and bool(self._client and self._client.is_connected)

    def status_snapshot(self) -> dict[str, Any]:
        """Return known state without connecting or waking the robot."""
        return {
            "connected": self.is_connected,
            "connection_status": (
                "connecting" if self._connecting else
                "connected" if self.is_connected else "disconnected"
            ),
            "nearby": self._nearby,
            "last_seen": self._last_seen,
            "last_communication": self._last_communication,
            "battery_updated_at": self._battery_updated_at,
            "last_error": self._last_error,
            "battery": self._last_battery,
            "asleep": self._is_asleep,
            "sleep_state_source": self._sleep_state_source,
            "stance": self._last_stance,
            "front_led": self._front_led,
            "back_led": self._back_led,
            "logic_displays": self._logic_displays,
            "holo_projector": self._holo_projector,
            "head_position": self._head_position,
        }

    async def async_disconnect(self) -> None:
        """Disconnect from the robot."""
        async with self._lock:
            await self._async_disconnect_locked()

    async def async_shutdown(self) -> None:
        """Prevent queued polls or actions from reconnecting after unload."""
        self._stopped = True
        self.set_state_callback(None)
        await self.async_disconnect()

    async def _async_disconnect_locked(self) -> None:
        client = self._client
        self._client = None
        self._connected = False
        self._notification_buffers.clear()
        self._publish_state()
        if client and client.is_connected:
            try:
                async with asyncio.timeout(15):
                    await client.disconnect()
            except (BleakError, TimeoutError):
                _LOGGER.debug("Disconnect failed for %s", self.address, exc_info=True)

    def _async_get_ble_device(self):
        return bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )

    async def _ensure_connected_locked(self) -> BleakClient:
        if self._stopped:
            raise R2D2Error("R2-D2 integration is unloading")
        client = self._client
        if client and client.is_connected:
            return client

        self._client = None
        self._connected = False

        ble_device = self._async_get_ble_device()
        if ble_device is None:
            reason = ""
            diagnostics = getattr(bluetooth, "async_address_reachability_diagnostics", None)
            intent = getattr(bluetooth, "BluetoothReachabilityIntent", None)
            if diagnostics is not None and intent is not None:
                reason = f". {diagnostics(self.hass, self.address, intent.CONNECTION)}"
            raise R2D2NotFoundError(
                f"R2-D2 device {self.address} is not currently available to Home Assistant{reason}"
            )

        _LOGGER.debug("Connecting to R2-D2 at %s", self.address)
        self._connecting = True
        self._publish_state()
        try:
            client = await establish_connection(
                BleakClientWithServiceCache,
                ble_device,
                self.name,
                disconnected_callback=self._disconnected,
                max_attempts=3,
                use_services_cache=True,
            )
            self._client = client
            self._notification_buffers.clear()
            async with asyncio.timeout(30):
                await self._async_initialize_protocol(client)
            if self._client is not client or not client.is_connected:
                raise R2D2Error("R2-D2 disconnected during initialization")
            self._connected = True
            self._last_error = None
            self._next_retry = 0.0
            self._retry_delay = 60.0
        except BaseException:
            await self._async_disconnect_locked()
            raise
        finally:
            self._connecting = False
            self._publish_state()
        return client

    async def _async_initialize_protocol(self, client: BleakClient) -> None:
        """Perform the auth/notify handshake copied from the .ino sketch."""
        def notification_callback(channel: str):
            def received(handle, data):
                self._notification_handler(handle, data, client=client, channel=channel)
            return received

        try:
            await client.start_notify(R2_CHAR_NOTIFY_1, notification_callback(R2_CHAR_NOTIFY_1))
        except BleakError:
            _LOGGER.debug(
                "Optional notification channel unavailable for %s", self.address, exc_info=True,
            )

        await client.write_gatt_char(R2_CHAR_AUTH, AUTH_MESSAGE, response=True)

        await client.start_notify(R2_CHAR_CMD, notification_callback(R2_CHAR_CMD))

        await asyncio.sleep(0.3)

    def _disconnected(self, client: BleakClient) -> None:
        if client is not self._client:
            return
        self._client = None
        self._connected = False
        self._notification_buffers.clear()
        self._publish_state()

    def _notification_handler(
        self, _handle, data: bytearray, *, client: BleakClient, channel: str,
    ) -> None:
        """Collect framed Sphero packets across BLE notification fragments."""
        if self._stopped or client is not self._client:
            return
        for byte in data:
            if byte == ESCAPE_START:
                self._notification_buffers[channel] = bytearray()
            elif byte == ESCAPE_END:
                frame = self._notification_buffers.pop(channel, None)
                if frame is not None:
                    self._process_notification_frame(frame)
            elif (frame := self._notification_buffers.get(channel)) is not None:
                frame.append(byte)
                if len(frame) > 4096:
                    self._notification_buffers.pop(channel, None)

    def _process_notification_frame(self, frame: bytearray) -> None:
        """Validate v2 checksum/header before accepting did-sleep (0x13/0x1A)."""
        decoded = bytearray()
        escaping = False
        escape_values = {0x23: ESCAPE_ESCAPE, 0x05: ESCAPE_START, 0x50: ESCAPE_END}
        for byte in frame:
            if escaping:
                if byte not in escape_values:
                    return
                decoded.append(escape_values[byte])
                escaping = False
            elif byte == ESCAPE_ESCAPE:
                escaping = True
            else:
                decoded.append(byte)
        if escaping or len(decoded) < 5 or (sum(decoded) & 0xFF) != 0xFF:
            return
        flags = decoded[0]
        if flags & 0x80:  # Extended flags are not supported by this decoder.
            return
        offset = 1 + bool(flags & 0x10) + bool(flags & 0x20)
        if len(decoded) < offset + 4:
            return
        device, command, sequence = decoded[offset:offset + 3]
        if device != 0x13 or flags & 0x01 or sequence != 0xFF:
            return
        _LOGGER.debug("R2-D2 power notification: command=0x%02x", command)
        # Will-sleep (0x19) is a warning, not confirmation of sleep.
        if command == 0x1A and len(decoded) == offset + 4:
            self._is_asleep = True
            self._sleep_state_source = "notification"
            self._startup_wake_pending = False
            self._last_communication = datetime.now(timezone.utc)
            self._publish_state()

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
        allow_disconnect: bool = False,
    ) -> None:
        current_client = client or await self._ensure_connected_locked()
        packet = self._build_packet(device, command, payload)
        async with asyncio.timeout(15):
            await current_client.write_gatt_char(R2_CHAR_CMD, packet, response=False)
        if not allow_disconnect and (
            self._client is not current_client or not current_client.is_connected
        ):
            raise R2D2Error("R2-D2 disconnected while sending a command")
        self._last_communication = datetime.now(timezone.utc)
        self._last_error = None

    async def async_send_command(
        self, device: int, command: int, payload: bytes = b"", *,
        wake_delay: float = 0.0,
    ) -> None:
        """Send a raw R2-D2 packet."""
        async with self._lock:
            try:
                # Wake only for explicit user actions, never for status polling.
                if (device, command) not in ((0x13, 0x0D), (0x13, 0x01)):
                    await self._write_packet_locked(0x13, 0x0D, b"")
                    self._is_asleep = False
                    self._sleep_state_source = "command"
                    self._startup_wake_pending = False
                    if wake_delay:
                        self._publish_state()
                        # Keep the lock held so Sleep cannot interleave between
                        # waking the droid and sending the requested animation.
                        await asyncio.sleep(wake_delay)
                        if not self.is_connected:
                            raise R2D2Error("R2-D2 disconnected while waking")
                await self._write_packet_locked(device, command, payload)
                if (device, command) != (0x13, 0x01):
                    self._startup_wake_pending = False
            except (BleakError, TimeoutError, R2D2Error) as err:
                self._last_error = str(err) or type(err).__name__
                await self._async_disconnect_locked()
                raise R2D2Error(f"R2-D2 command failed: {self._last_error}") from err
            finally:
                self._publish_state()

    async def async_wake(self) -> None:
        await self.async_send_command(0x13, 0x0D)
        self._is_asleep = False
        self._sleep_state_source = "command"
        self._publish_state()

    async def async_sleep(self) -> None:
        # Keep the sleep command and disconnect atomic with respect to polls.
        async with self._lock:
            try:
                await self._write_packet_locked(0x13, 0x01, b"", allow_disconnect=True)
            except (BleakError, TimeoutError, R2D2Error) as err:
                self._last_error = str(err) or type(err).__name__
                await self._async_disconnect_locked()
                raise R2D2Error(f"R2-D2 sleep failed: {self._last_error}") from err
            self._is_asleep = True
            self._sleep_state_source = "command"
            self._startup_wake_pending = False
            await self._async_disconnect_locked()

    async def async_play_animation(self, animation_id: int) -> None:
        if not 0 <= animation_id <= 56:
            raise ValueError("animation_id must be between 0 and 56")
        await self.async_send_command(
            0x17, 0x05, bytes((0x00, animation_id)), wake_delay=0.5,
        )
        self._is_asleep = False

    async def async_set_stance(self, stance: str) -> None:
        if stance not in STANCE_TO_VALUE:
            raise ValueError(f"Unsupported stance: {stance}")
        await self.async_send_command(0x17, 0x0D, bytes((STANCE_TO_VALUE[stance],)))
        self._last_stance = stance
        self._is_asleep = False

    async def async_set_head_position(self, position: float) -> None:
        clamped = max(float(HEAD_POSITION_MIN), min(float(HEAD_POSITION_MAX), float(position)))
        await self.async_send_command(
            ANIMATRONIC_DEVICE_ID,
            ANIMATRONIC_SET_HEAD_POSITION,
            struct.pack(">f", clamped),
        )
        self._head_position = clamped
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

    async def async_startup(self) -> dict[str, Any]:
        """Request an initial wake, retrying when a powered-off droid returns."""
        if not self._is_asleep and not self._stopped:
            self._startup_wake_pending = True
        return await self.async_get_status()

    async def async_get_status(self) -> dict[str, Any]:
        """Read status, respecting intentional sleep and reconnect backoff."""
        async with self._lock:
            if self._stopped or self._is_asleep or (
                not self.is_connected and monotonic() < self._next_retry
            ):
                return self.status_snapshot()
            try:
                client = await self._ensure_connected_locked()
                if self._startup_wake_pending:
                    await self._write_packet_locked(0x13, 0x0D, b"", client=client)
                    self._startup_wake_pending = False
                    self._is_asleep = False
                    self._sleep_state_source = "command"
                async with asyncio.timeout(15):
                    raw = await client.read_gatt_char(BATTERY_CHAR_UUID)
                if raw:
                    self._last_battery = int(raw[0])
                    self._battery_updated_at = datetime.now(timezone.utc)
                    self._last_communication = self._battery_updated_at
                    self._last_error = None
            except (BleakError, TimeoutError, R2D2Error) as err:
                _LOGGER.debug("Status read failed for %s", self.address, exc_info=True)
                self._last_error = str(err) or type(err).__name__
                if self._startup_wake_pending:
                    await self._async_disconnect_locked()
                if not self.is_connected:
                    self._next_retry = monotonic() + self._retry_delay
                    self._retry_delay = min(self._retry_delay * 2, 300.0)
            return self.status_snapshot()

    @property
    def is_asleep(self) -> bool:
        return self._is_asleep
