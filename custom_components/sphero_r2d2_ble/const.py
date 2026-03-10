"""Constants for the Sphero R2-D2 BLE integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "sphero_r2d2_ble"
PLATFORMS = ["sensor", "binary_sensor", "button", "number", "select"]

CONF_ADDRESS = "address"
CONF_NAME = "name"
DEFAULT_NAME = "Sphero R2-D2"

UPDATE_INTERVAL = timedelta(seconds=60)
SLEEP_TIMEOUT_SECONDS = 600

SERVICE_PLAY_ANIMATION = "play_animation"
SERVICE_SET_STANCE = "set_stance"

STANCE_BIPOD = "bipod"
STANCE_TRIPOD = "tripod"
STANCE_TO_VALUE = {
    STANCE_TRIPOD: 1,
    STANCE_BIPOD: 2,
}
VALUE_TO_STANCE = {value: key for key, value in STANCE_TO_VALUE.items()}

R2_SERVICE_AUTH = "00020001-574f-4f20-5370-6865726f2121"
R2_CHAR_AUTH = "00020005-574f-4f20-5370-6865726f2121"
R2_CHAR_NOTIFY_1 = "00020002-574f-4f20-5370-6865726f2121"
R2_SERVICE_CMD = "00010001-574f-4f20-5370-6865726f2121"
R2_CHAR_CMD = "00010002-574f-4f20-5370-6865726f2121"
AUTH_MESSAGE = b"usetheforce...band"

BATTERY_SERVICE_UUID = "0000180f-0000-1000-8000-00805f9b34fb"
BATTERY_CHAR_UUID = "00002a19-0000-1000-8000-00805f9b34fb"
