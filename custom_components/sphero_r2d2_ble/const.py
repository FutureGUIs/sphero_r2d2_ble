"""Constants for the Sphero R2-D2 BLE integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "sphero_r2d2_ble"
PLATFORMS = ["sensor", "binary_sensor", "button", "select"]

CONF_ADDRESS = "address"
CONF_NAME = "name"
DEFAULT_NAME = "Sphero R2-D2"
R2_NAME_PREFIXES: tuple[str, ...] = ("D2-", "Q5-")

UPDATE_INTERVAL = timedelta(seconds=60)
SLEEP_TIMEOUT_SECONDS = 600

SERVICE_PLAY_ANIMATION = "play_animation"
SERVICE_SET_STANCE = "set_stance"

STANCE_STOP = "Stop"
STANCE_BIPOD = "Bipod"
STANCE_TRIPOD = "Tripod"
STANCE_WADDLE = "Waddle"
STANCE_TO_VALUE = {
    STANCE_STOP: 0,
    STANCE_TRIPOD: 1,
    STANCE_BIPOD: 2,
    STANCE_WADDLE: 3,
}
VALUE_TO_STANCE = {value: key for key, value in STANCE_TO_VALUE.items()}

ANIMATION_CHOICES = {
    "Charger 1 (0)": 0,
    "Charger 2 (1)": 1,
    "Charger 3 (2)": 2,
    "Charger 4 (3)": 3,
    "Charger 5 (4)": 4,
    "Charger 6 (5)": 5,
    "Charger 7 (6)": 6,
    "Emote Alarm (7)": 7,
    "Emote Angry (8)": 8,
    "Emote Annoyed (9)": 9,
    "Emote Chatty (10)": 10,
    "Emote Drive (11)": 11,
    "Emote Excited (12)": 12,
    "Emote Happy (13)": 13,
    "Emote Ion Blast (14)": 14,
    "Emote Laugh (15)": 15,
    "Emote No (16)": 16,
    "Emote Sad (17)": 17,
    "Emote Sassy (18)": 18,
    "Emote Scared (19)": 19,
    "Emote Spin (20)": 20,
    "Emote Yes (21)": 21,
    "Emote Scan (22)": 22,
    "Emote Sleep (23)": 23,
    "Emote Surprised (24)": 24,
    "Idle 1 (25)": 25,
    "Idle 2 (26)": 26,
    "Idle 3 (27)": 27,
    "Patrol Alarm (28)": 28,
    "Patrol Hit (29)": 29,
    "Patrol Patrolling (30)": 30,
    "WWM Angry (31)": 31,
    "WWM Anxious (32)": 32,
    "WWM Bow (33)": 33,
    "WWM Concern (34)": 34,
    "WWM Curious (35)": 35,
    "WWM Double Take (36)": 36,
    "WWM Excited (37)": 37,
    "WWM Fiery (38)": 38,
    "WWM Frustrated (39)": 39,
    "WWM Happy (40)": 40,
    "WWM Jittery (41)": 41,
    "WWM Laugh (42)": 42,
    "WWM Long Shake (43)": 43,
    "WWM No (44)": 44,
    "WWM Ominous (45)": 45,
    "WWM Relieved (46)": 46,
    "WWM Sad (47)": 47,
    "WWM Scared (48)": 48,
    "WWM Shake (49)": 49,
    "WWM Surprised (50)": 50,
    "WWM Taunting (51)": 51,
    "WWM Whisper (52)": 52,
    "WWM Yelling (53)": 53,
    "WWM Yoohoo (54)": 54,
    "Motor (55)": 55,
}
ANIMATION_OPTIONS = list(ANIMATION_CHOICES)
ANIMATION_ID_TO_OPTION = {value: key for key, value in ANIMATION_CHOICES.items()}

R2_SERVICE_AUTH = "00020001-574f-4f20-5370-6865726f2121"
R2_CHAR_AUTH = "00020005-574f-4f20-5370-6865726f2121"
R2_CHAR_NOTIFY_1 = "00020002-574f-4f20-5370-6865726f2121"
R2_SERVICE_CMD = "00010001-574f-4f20-5370-6865726f2121"
R2_CHAR_CMD = "00010002-574f-4f20-5370-6865726f2121"
AUTH_MESSAGE = b"usetheforce...band"

BATTERY_SERVICE_UUID = "0000180f-0000-1000-8000-00805f9b34fb"
BATTERY_CHAR_UUID = "00002a19-0000-1000-8000-00805f9b34fb"
