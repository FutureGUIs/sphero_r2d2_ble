"""Transport regression tests with fake BLE/HA dependencies; no hardware needed.

Run with: python -m unittest discover -s tests -v
These tests exercise API logic, not Home Assistant's Bluetooth backend.
"""

import importlib.util
import asyncio
import logging
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch


COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "sphero_r2d2_ble"


class FakeBleakError(Exception):
    pass


class FakeClient:
    def __init__(self):
        self.is_connected = True
        self.writes = []
        self.reads = 0
        self.callback = None
        self.read_error = None
        self.write_error = None
        self.notify_error_uuid = None
        self.drop_on_write = False
        self.notifications = {}

    async def start_notify(self, uuid, callback):
        if uuid == self.notify_error_uuid:
            raise FakeBleakError("notification setup failed")
        self.notifications[uuid] = callback

    def notify(self, uuid, data):
        self.notifications[uuid](uuid, bytearray(data))

    async def write_gatt_char(self, uuid, data, response):
        if self.write_error:
            raise self.write_error
        self.writes.append((uuid, data, response))
        if self.drop_on_write:
            self.drop()

    async def read_gatt_char(self, uuid):
        self.reads += 1
        if self.read_error:
            raise self.read_error
        return bytes([75])

    def drop(self):
        self.is_connected = False
        if self.callback:
            self.callback(self)

    async def disconnect(self):
        self.drop()


class FakeCoordinator:
    def __class_getitem__(cls, item):
        return cls

    def __init__(self, *args, **kwargs):
        self.data = None
        self.updates = 0

    def async_set_updated_data(self, data):
        self.data = data
        self.last_update_success = True
        self.updates += 1


def module(name, **attributes):
    result = ModuleType(name)
    result.__dict__.update(attributes)
    return result


class ConnectionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        bluetooth = SimpleNamespace(async_ble_device_from_address=lambda *args, **kwargs: object())
        package = module("_r2d2_tests", __path__=[str(COMPONENT)])
        dependencies = {
            "_r2d2_tests": package,
            "bleak": module("bleak", BleakClient=FakeClient),
            "bleak.exc": module("bleak.exc", BleakError=FakeBleakError),
            "bleak_retry_connector": module(
                "bleak_retry_connector", establish_connection=AsyncMock(),
                BleakClientWithServiceCache=FakeClient,
            ),
            "homeassistant": module("homeassistant"),
            "homeassistant.components": module("homeassistant.components", bluetooth=bluetooth),
            "homeassistant.core": module("homeassistant.core", HomeAssistant=object),
            "homeassistant.helpers": module("homeassistant.helpers"),
            "homeassistant.helpers.update_coordinator": module(
                "homeassistant.helpers.update_coordinator",
                DataUpdateCoordinator=FakeCoordinator, UpdateFailed=RuntimeError,
            ),
        }
        modules_patch = patch.dict(sys.modules, dependencies)
        modules_patch.start()
        self.addCleanup(modules_patch.stop)
        for name in ("const", "api", "coordinator"):
            qualified_name = f"_r2d2_tests.{name}"
            spec = importlib.util.spec_from_file_location(qualified_name, COMPONENT / f"{name}.py")
            loaded = importlib.util.module_from_spec(spec)
            sys.modules[qualified_name] = loaded
            spec.loader.exec_module(loaded)
            setattr(self, name + "_module", loaded)
        self.api = self.api_module.R2D2Api(object(), "AA:BB", "R2-D2")
        self.coordinator = self.coordinator_module.R2D2Coordinator(
            object(), logging.getLogger(__name__), self.api,
        )
        self.clients = []

        async def connect(*args, **kwargs):
            client = FakeClient()
            client.callback = kwargs["disconnected_callback"]
            self.clients.append(client)
            return client

        self.connect = AsyncMock(side_effect=connect)
        self.api_module.establish_connection = self.connect
        delay_patch = patch.object(self.api_module.asyncio, "sleep", new=AsyncMock())
        delay_patch.start()
        self.addCleanup(delay_patch.stop)

    async def test_poll_connects_without_sending_wake(self):
        status = await self.api.async_get_status()
        self.assertTrue(status["connected"])
        self.assertEqual(status["battery"], 75)
        self.assertEqual(len(self.clients[0].writes), 1)  # Authentication only.
        self.assertIsNotNone(status["battery_updated_at"])

    async def test_disconnect_publishes_immediately(self):
        await self.api.async_get_status()
        self.clients[0].drop()
        self.assertFalse(self.coordinator.data["connected"])
        self.assertEqual(self.coordinator.data["connection_status"], "disconnected")
        self.assertIsNone(self.api._client)

    async def test_old_disconnect_cannot_clear_new_connection(self):
        await self.api.async_get_status()
        old = self.clients[0]
        old.drop()
        await self.api.async_get_status()
        old.callback(old)
        self.assertTrue(self.api.is_connected)
        self.assertTrue(self.coordinator.data["connected"])

    async def test_sleep_suspends_polling_and_explicit_wake_resumes(self):
        await self.api.async_get_status()
        await self.api.async_sleep()
        status = await self.api.async_get_status()
        self.assertTrue(status["asleep"])
        self.assertFalse(status["connected"])
        self.assertEqual(self.connect.await_count, 1)
        self.assertEqual(self.clients[0].reads, 1)
        await self.api.async_wake()
        self.assertFalse(self.api.is_asleep)
        self.assertTrue(self.api.is_connected)
        self.assertEqual(self.connect.await_count, 2)

    async def test_sleep_accepts_expected_disconnect_after_write(self):
        await self.api.async_get_status()
        self.clients[0].drop_on_write = True
        await self.api.async_sleep()
        self.assertTrue(self.api.is_asleep)
        self.assertFalse(self.api.is_connected)

    async def test_animation_wakes_after_sleep(self):
        await self.api.async_sleep()
        await self.api.async_play_animation(7)
        self.assertFalse(self.api.is_asleep)
        self.assertTrue(self.api.is_connected)
        self.assertEqual(len(self.clients[-1].writes), 3)  # Auth, wake, animation.

    async def test_animation_waits_between_wake_and_animation(self):
        await self.api.async_sleep()
        events = []
        write = self.api._write_packet_locked

        async def record_write(device, command, payload, **kwargs):
            await write(device, command, payload, **kwargs)
            events.append((device, command))

        async def record_delay(seconds):
            if seconds == 0.5:
                events.append("wake delay")

        with patch.object(self.api, "_write_packet_locked", side_effect=record_write):
            with patch.object(self.api_module.asyncio, "sleep", side_effect=record_delay):
                await self.api.async_play_animation(7)
        self.assertEqual(events, [(0x13, 0x0D), "wake delay", (0x17, 0x05)])

    async def test_animation_does_not_run_if_wake_fails(self):
        await self.api.async_get_status()
        self.clients[0].write_error = FakeBleakError("wake failed")
        with self.assertRaises(self.api_module.R2D2Error):
            await self.api.async_play_animation(7)
        self.assertEqual(len(self.clients[0].writes), 1)  # Authentication only.

    async def test_animation_does_not_reconnect_without_wake_after_delay_drop(self):
        await self.api.async_get_status()
        client = self.clients[0]

        async def drop_during_delay(seconds):
            client.drop()

        with patch.object(self.api_module.asyncio, "sleep", side_effect=drop_during_delay):
            with self.assertRaises(self.api_module.R2D2Error):
                await self.api.async_play_animation(7)
        self.assertEqual(self.connect.await_count, 1)
        self.assertEqual(len(client.writes), 2)  # Auth and wake, no animation.

    async def test_animation_reports_unreachable_droid_without_sending(self):
        self.api_module.bluetooth.async_ble_device_from_address = lambda *args, **kwargs: None
        with self.assertRaises(self.api_module.R2D2Error):
            await self.api.async_play_animation(7)
        self.connect.assert_not_awaited()
        self.assertFalse(self.api.is_connected)

    def power_notification(self, command=0x1A, *, routing=False, response=False):
        header = bytearray([0x30 if routing else 0])
        if response:
            header[0] |= 1
        if routing:
            header.extend([0x8D, 0xAB])
        header.extend([0x13, command, 0xFF])
        if response:
            header.append(0)
        header.append((0xFF - sum(header)) & 0xFF)
        encoded = bytearray([0x8D])
        for byte in header:
            encoded.extend({0x8D: b"\xab\x05", 0xAB: b"\xab\x23", 0xD8: b"\xab\x50"}.get(byte, bytes([byte])))
        encoded.append(0xD8)
        return encoded

    async def test_automatic_sleep_notification_publishes_immediately(self):
        await self.api.async_get_status()
        # Known v2 did-sleep packet: flags, DID, CID, SEQ, checksum.
        self.clients[0].notify(self.api_module.R2_CHAR_CMD, b"\x8d\x00\x13\x1a\xff\xd3\xd8")
        self.assertTrue(self.coordinator.data["asleep"])
        self.assertEqual(self.coordinator.data["sleep_state_source"], "notification")
        self.assertTrue(self.coordinator.data["connected"])
        await self.api.async_get_status()
        self.assertEqual(self.clients[0].reads, 1)  # No polling/waking a sleeping droid.

    async def test_fragmented_sleep_notification(self):
        await self.api.async_get_status()
        client = self.clients[0]
        packet = self.power_notification()
        for byte in packet[:-1]:
            client.notify(self.api_module.R2_CHAR_CMD, bytes([byte]))
        self.assertFalse(self.api.is_asleep)
        client.notify(self.api_module.R2_CHAR_CMD, packet[-1:])
        self.assertTrue(self.api.is_asleep)

    async def test_routed_escaped_sleep_notification(self):
        await self.api.async_get_status()
        self.clients[0].notify(self.api_module.R2_CHAR_CMD, self.power_notification(routing=True))
        self.assertTrue(self.api.is_asleep)

    async def test_sleep_warning_does_not_mark_droid_asleep(self):
        await self.api.async_get_status()
        self.clients[0].notify(self.api_module.R2_CHAR_CMD, self.power_notification(command=0x19))
        self.assertFalse(self.api.is_asleep)

    async def test_response_packet_does_not_masquerade_as_sleep_event(self):
        await self.api.async_get_status()
        self.clients[0].notify(self.api_module.R2_CHAR_CMD, self.power_notification(response=True))
        self.assertFalse(self.api.is_asleep)

    async def test_invalid_notification_is_ignored_and_parser_recovers(self):
        await self.api.async_get_status()
        client = self.clients[0]
        bad_checksum = self.power_notification()
        bad_checksum[-2] ^= 1
        for packet in (
            bad_checksum, b"\x8d\xab\x99\xd8", b"\x8d\xab\xd8",
            b"\x8d\x30\xff\xd8", b"\x8d" + b"\x00" * 5000 + b"\xd8",
        ):
            client.notify(self.api_module.R2_CHAR_CMD, packet)
            self.assertFalse(self.api.is_asleep)
        client.notify(self.api_module.R2_CHAR_CMD, self.power_notification())
        self.assertTrue(self.api.is_asleep)

    async def test_notification_channels_do_not_share_partial_packets(self):
        await self.api.async_get_status()
        packet = self.power_notification()
        client = self.clients[0]
        client.notify(self.api_module.R2_CHAR_CMD, packet[:4])
        client.notify(self.api_module.R2_CHAR_NOTIFY_1, packet[4:])
        self.assertFalse(self.api.is_asleep)
        client.notify(self.api_module.R2_CHAR_CMD, packet[4:])
        self.assertTrue(self.api.is_asleep)

    async def test_notifications_from_old_connection_are_ignored(self):
        await self.api.async_get_status()
        old = self.clients[0]
        old.drop()
        await self.api.async_get_status()
        old.notify(self.api_module.R2_CHAR_CMD, self.power_notification())
        self.assertFalse(self.api.is_asleep)

    async def test_wake_clears_automatic_sleep_status_immediately(self):
        await self.api.async_get_status()
        self.clients[0].notify(self.api_module.R2_CHAR_CMD, self.power_notification())
        await self.api.async_wake()
        self.assertFalse(self.coordinator.data["asleep"])
        self.assertEqual(self.coordinator.data["sleep_state_source"], "command")

    async def test_concatenated_notifications(self):
        await self.api.async_get_status()
        self.clients[0].notify(
            self.api_module.R2_CHAR_CMD,
            self.power_notification(command=0x19) + self.power_notification(),
        )
        self.assertTrue(self.api.is_asleep)

    async def test_reconnect_backoff_and_user_bypass(self):
        self.connect.side_effect = FakeBleakError("proxy unavailable")
        with patch.object(self.api_module, "monotonic", return_value=100):
            status = await self.api.async_get_status()
            self.assertFalse(status["connected"])
            self.assertEqual(status["last_error"], "proxy unavailable")
            await self.api.async_get_status()
            self.assertEqual(self.connect.await_count, 1)
        with patch.object(self.api_module, "monotonic", return_value=160):
            await self.api.async_get_status()
            self.assertEqual(self.api._next_retry, 280)
        with self.assertRaises(self.api_module.R2D2Error):
            await self.api.async_wake()
        self.assertEqual(self.connect.await_count, 3)

    async def test_command_failure_clears_connection_and_reports_error(self):
        await self.api.async_get_status()
        self.clients[0].write_error = FakeBleakError("write failed")
        with self.assertRaises(self.api_module.R2D2Error):
            await self.api.async_wake()
        self.assertFalse(self.coordinator.data["connected"])
        self.assertEqual(self.coordinator.data["last_error"], "write failed")

    async def test_failed_battery_read_preserves_connection_and_timestamp(self):
        status = await self.api.async_get_status()
        self.clients[0].read_error = FakeBleakError("battery unavailable")
        failed = await self.api.async_get_status()
        self.assertTrue(failed["connected"])
        self.assertEqual(failed["battery"], 75)
        self.assertEqual(failed["battery_updated_at"], status["battery_updated_at"])
        self.assertEqual(failed["last_error"], "battery unavailable")

    async def test_required_notification_failure_does_not_report_connected(self):
        client = FakeClient()
        client.notify_error_uuid = self.api_module.R2_CHAR_CMD
        self.connect.side_effect = None
        self.connect.return_value = client
        status = await self.api.async_get_status()
        self.assertFalse(status["connected"])
        self.assertFalse(client.is_connected)
        self.assertEqual(status["last_error"], "notification setup failed")

    async def test_auth_failure_does_not_report_connected(self):
        client = FakeClient()
        client.write_error = FakeBleakError("auth failed")
        self.connect.side_effect = None
        self.connect.return_value = client
        status = await self.api.async_get_status()
        self.assertFalse(status["connected"])
        self.assertFalse(client.is_connected)
        self.assertEqual(status["last_error"], "auth failed")

    async def test_optimistic_entity_update_cannot_overwrite_disconnect(self):
        await self.api.async_get_status()
        self.clients[0].drop()
        self.coordinator.async_update_local_state(connected=True)
        self.assertFalse(self.coordinator.data["connected"])

    async def test_presence_does_not_override_connection_or_starve_polling(self):
        await self.api.async_get_status()
        self.api.async_update_presence(True)
        updates = self.coordinator.updates
        self.api.async_update_presence(True)
        self.assertEqual(self.coordinator.updates, updates)
        self.api.async_update_presence(False)
        self.assertTrue(self.coordinator.data["connected"])
        self.assertFalse(self.coordinator.data["nearby"])

    async def test_detached_listener_is_not_called_on_disconnect(self):
        await self.api.async_get_status()
        updates = self.coordinator.updates
        self.api.set_state_callback(None)
        await self.api.async_disconnect()
        self.assertEqual(self.coordinator.updates, updates)


    async def test_shutdown_prevents_queued_poll_and_command_reconnect(self):
        await self.api.async_get_status()
        await self.api.async_shutdown()
        status = await self.api.async_get_status()
        self.assertFalse(status["connected"])
        with self.assertRaises(self.api_module.R2D2Error):
            await self.api.async_wake()
        self.assertEqual(self.connect.await_count, 1)

    async def test_cancellation_during_initialization_disconnects_client(self):
        with patch.object(self.api_module.asyncio, "sleep", new=AsyncMock(side_effect=asyncio.CancelledError)):
            with self.assertRaises(asyncio.CancelledError):
                await self.api.async_get_status()
        self.assertFalse(self.clients[0].is_connected)
        self.assertFalse(self.api.is_connected)
        self.assertFalse(self.api._connecting)

    async def test_optional_notification_failure_is_tolerated(self):
        client = FakeClient()
        client.notify_error_uuid = self.api_module.R2_CHAR_NOTIFY_1
        self.connect.side_effect = None
        self.connect.return_value = client
        status = await self.api.async_get_status()
        self.assertTrue(status["connected"])

    async def test_write_timeout_disconnects_and_reports_error(self):
        await self.api.async_get_status()
        self.clients[0].write_error = TimeoutError()
        with self.assertRaises(self.api_module.R2D2Error):
            await self.api.async_wake()
        self.assertFalse(self.coordinator.data["connected"])
        self.assertEqual(self.coordinator.data["last_error"], "TimeoutError")

    async def test_missing_device_uses_optional_reachability_diagnostics(self):
        bluetooth = self.api_module.bluetooth
        bluetooth.async_ble_device_from_address = lambda *args, **kwargs: None
        bluetooth.async_address_reachability_diagnostics = lambda *args: "No connectable adapters"
        bluetooth.BluetoothReachabilityIntent = SimpleNamespace(CONNECTION=object())
        status = await self.api.async_get_status()
        self.assertFalse(status["connected"])
        self.assertIn("No connectable adapters", status["last_error"])
        self.connect.assert_not_awaited()

    def load_integration(self, every_advertisement=False):
        """Import the actual package initializer and its conflicting submodule."""
        bluetooth = self.api_module.bluetooth
        bluetooth.async_address_present = lambda *args, **kwargs: False
        bluetooth.async_register_callback = lambda *args, **kwargs: lambda: None
        bluetooth.async_track_unavailable = lambda *args, **kwargs: lambda: None
        bluetooth.BluetoothScanningMode = SimpleNamespace(PASSIVE=object())
        if every_advertisement:
            bluetooth.async_register_advertisement_callback = lambda *args, **kwargs: lambda: None
        vol = module(
            "voluptuous", Schema=lambda value: value, Required=lambda value: value,
            Optional=lambda value: value, All=lambda *args: args,
            Coerce=lambda value: value, Range=lambda **kwargs: None, In=lambda value: value,
        )
        dependencies = {
            "voluptuous": vol,
            "homeassistant.config_entries": module("homeassistant.config_entries", ConfigEntry=object),
            "homeassistant.exceptions": module("homeassistant.exceptions", HomeAssistantError=RuntimeError),
            "homeassistant.helpers.typing": module("homeassistant.helpers.typing", ConfigType=dict),
        }
        sys.modules["homeassistant.core"].ServiceCall = object
        helpers = sys.modules["homeassistant.helpers"]
        helpers.config_validation = SimpleNamespace(entity_id=str, string=str)
        helpers.device_registry = SimpleNamespace()
        modules_patch = patch.dict(sys.modules, dependencies)
        modules_patch.start()
        self.addCleanup(modules_patch.stop)
        spec = importlib.util.spec_from_file_location(
            "_r2d2_tests", COMPONENT / "__init__.py", submodule_search_locations=[str(COMPONENT)],
        )
        integration = importlib.util.module_from_spec(spec)
        sys.modules["_r2d2_tests"] = integration
        spec.loader.exec_module(integration)
        local_bluetooth = importlib.import_module("_r2d2_tests.bluetooth")
        self.assertIs(integration.bluetooth, local_bluetooth)
        self.assertIs(integration.ha_bluetooth, bluetooth)
        return integration

    async def setup_offline_integration(self, every_advertisement=False):
        integration = self.load_integration(every_advertisement)
        self.api_module.bluetooth.async_ble_device_from_address = lambda *args, **kwargs: None
        tasks = []
        entry = SimpleNamespace(
            data={"address": "AA:BB", "name": "R2-D2"}, entry_id="r2d2",
            async_on_unload=lambda callback: None,
            async_create_background_task=lambda hass, target, name: tasks.append(target),
        )
        self.addCleanup(lambda: [task.close() for task in tasks])
        hass = SimpleNamespace(
            data={integration.DOMAIN: {}},
            config_entries=SimpleNamespace(async_forward_entry_setups=AsyncMock()),
        )
        self.assertTrue(await integration.async_setup_entry(hass, entry))
        hass.config_entries.async_forward_entry_setups.assert_awaited_once()
        self.connect.assert_not_awaited()
        self.assertFalse(entry.runtime_data.coordinator.data["connected"])
        self.assertTrue(entry.runtime_data.coordinator.last_update_success)
        self.assertEqual(len(tasks), 1)
        await tasks[0]
        self.assertFalse(entry.runtime_data.coordinator.data["connected"])
        self.assertTrue(entry.runtime_data.coordinator.last_update_success)
        self.assertIn("not currently available", entry.runtime_data.coordinator.data["last_error"])
        return entry.runtime_data

    async def test_actual_setup_survives_local_bluetooth_import_and_offline_droid(self):
        await self.setup_offline_integration()

    async def test_actual_setup_with_new_advertisement_api_stays_loaded_offline(self):
        await self.setup_offline_integration(every_advertisement=True)

    async def test_offline_startup_wake_retries_when_droid_returns(self):
        runtime = await self.setup_offline_integration()
        self.api_module.bluetooth.async_ble_device_from_address = lambda *args, **kwargs: object()
        with patch.object(self.api_module, "monotonic", return_value=runtime.api._next_retry):
            status = await runtime.api.async_get_status()
        self.assertTrue(status["connected"])
        self.assertFalse(runtime.api._startup_wake_pending)
        self.assertEqual(len(self.clients[-1].writes), 2)  # Auth, startup wake.
        await runtime.api.async_get_status()
        self.assertEqual(len(self.clients[-1].writes), 2)  # Subsequent polls never wake.

    async def test_failed_startup_connection_keeps_loaded_entities(self):
        self.load_integration()
        self.connect.side_effect = FakeBleakError("proxy offline")
        coordinator = self.coordinator
        await coordinator.async_startup()
        self.assertFalse(coordinator.data["connected"])
        self.assertEqual(coordinator.data["last_error"], "proxy offline")
        self.assertTrue(coordinator.last_update_success)

    async def test_sleep_cancels_pending_startup_wake(self):
        self.api._startup_wake_pending = True
        await self.api.async_sleep()
        self.assertFalse(self.api._startup_wake_pending)
        await self.api.async_get_status()
        self.assertEqual(self.connect.await_count, 1)

    async def test_actual_setup_loads_and_wakes_online_droid(self):
        integration = self.load_integration()
        tasks = []
        entry = SimpleNamespace(
            data={"address": "AA:BB", "name": "R2-D2"}, entry_id="r2d2",
            async_on_unload=lambda callback: None,
            async_create_background_task=lambda hass, target, name: tasks.append(target),
        )
        self.addCleanup(lambda: [task.close() for task in tasks])
        hass = SimpleNamespace(
            data={integration.DOMAIN: {}},
            config_entries=SimpleNamespace(async_forward_entry_setups=AsyncMock()),
        )
        self.assertTrue(await integration.async_setup_entry(hass, entry))
        hass.config_entries.async_forward_entry_setups.assert_awaited_once()
        await tasks[0]
        self.assertTrue(entry.runtime_data.coordinator.data["connected"])
        self.assertTrue(entry.runtime_data.coordinator.last_update_success)
        self.assertEqual(len(self.clients[0].writes), 2)  # Authentication and wake.


if __name__ == "__main__":
    unittest.main()
