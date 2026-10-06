# Sphero R2-D2 BLE custom integration

Control a Sphero R2-D2 through Home Assistant's Bluetooth adapters and ESPHome
Bluetooth proxies, without dedicated R2-D2 bridge firmware. Requires Home
Assistant 2026.3.0 or later and a Bluetooth adapter/proxy that supports connections.

The original BLE command logic comes from
[HA-Control-Sphero-R2D2](https://github.com/h311m4n000/HA-Control-Sphero-R2D2)
and its `r2d2_ha_tiny.ino` sketch. Thanks to
[h311m4n000](https://github.com/h311m4n000) for that work.

## Included features

- Config flow with automatic Bluetooth discovery
- Native BLE connection through Home Assistant Bluetooth adapters and proxies
- Wake and sleep buttons
- Animation select entity plus play-animation button
- Front and back RGB LED light entities
- Logic display and holo projector brightness light entities
- Head rotation slider entity
- Battery, connected, nearby, and asleep entities
- Stance select entity (`Stop` / `Bipod` / `Tripod` / `Waddle`)
- `sphero_r2d2_ble.play_animation` service
- `sphero_r2d2_ble.set_stance` service

## Install

HACS:

1. Add this repository to HACS as a custom repository of type `Integration`
2. Install **Sphero R2-D2 BLE**
3. Restart Home Assistant

Manual:

1. Copy `custom_components/sphero_r2d2_ble` into `config/custom_components/`
2. Restart Home Assistant

## Setup

1. Put the droid in range of a Home Assistant Bluetooth adapter or proxy
2. Home Assistant should discover it automatically
3. If discovery does not appear, add **Sphero R2-D2 BLE** from **Settings > Devices & Services > Add Integration**
4. Enter the Bluetooth MAC address for the droid

## Notes

- The command packet builder, UUIDs, auth string, wake/sleep/animation/stance commands, and battery read are translated from the referenced `.ino` sketch.
- Animation names map to the known ID list used by the toy.
- The toy must be reachable by a Home Assistant Bluetooth adapter or ESPHome Bluetooth proxy.

## Connection status and sleep

- The integration loads its entities even when the droid is powered off or out of
  range. It attempts an initial wake in the background, retries if the droid is
  unreachable, and sends the pending wake once a BLE connection can be made.
  Wake controls remain available while disconnected. A physically powered-off
  Bluetooth radio must become reachable before any BLE wake command can be sent.
- **Connected** reflects an initialized, active BLE session. Transport disconnects
  update this entity immediately when Home Assistant's Bluetooth backend reports
  them; radio loss detection itself can take longer.
- **Nearby** reflects Bluetooth advertisements, independently of Connected. A
  connected droid may stop advertising, and a nearby droid may still refuse a
  connection. Advertisement loss can take several minutes to be reported.
- **Asleep** updates immediately on the droid's `did sleep` power notification,
  including automatic sleep. It also tracks successful HA sleep/wake actions.
  Its `state_source` attribute distinguishes `notification` from `command` (or
  `unknown` before any evidence). Command state reflects successful GATT writes;
  hardware notification support must be verified with your droid. State is not
  persisted through a Home Assistant restart.
- Sleep sends the sleep command, disconnects, and suspends status polling. Wake,
  animation, stance, head, and LED controls can reconnect and wake the droid.
- Play Animation reconnects if needed, sends Wake, waits 0.5 seconds for the droid
  to wake, then sends the selected animation. This sequence also applies to the
  play-animation service and stays locked against concurrent Sleep/poll commands.
- Regular status polling does not send wake commands after the initial startup
  wake succeeds or is canceled by Sleep. Failed background connections retry
  with delays of 60, 120, 240, then 300 seconds, evaluated on the normal 60-second
  polling schedule. Explicit controls bypass this delay.
- Connected attributes include `connection_status`, `last_communication`, and
  `last_error`. Communication means a successful GATT read/write, not confirmation
  that the robot performed an action. Battery exposes `last_updated` so a cached
  reading can be distinguished from a fresh one.
- Nearby exposes `last_seen`. Newer HA versions observe every advertisement;
  older versions observe changed advertisements only. Initial cached presence is
  recorded when the integration starts. Timestamp updates are published with
  the next status update to avoid frequent advertisements delaying battery polls.
- Authentication and command notification setup failures are now reported rather
  than silently ignored. The auxiliary notification channel remains optional.

## Local testing

Run the hardware-free regression suite from the repository directory:

```sh
python -m unittest discover -s tests -v
```

The tests use fake Home Assistant and BLE dependencies. Test the installed
integration with your real droid and Bluetooth adapter/proxy before committing:

1. Back up `config/custom_components/sphero_r2d2_ble`, then replace it with this
   checkout's `custom_components/sphero_r2d2_ble` directory and restart HA.
2. Check Connected, Nearby, and the diagnostic attributes. Test Wake, animation,
   stance, head rotation, and LEDs.
3. Press Sleep. Connected should turn off and Asleep on. Wait at least two minutes;
   the integration should leave the droid asleep. Press Wake to reconnect.
4. Interrupt the Bluetooth path while awake. Connected should turn off once the
   backend reports the disconnect. Restore the path and verify automatic recovery.
5. Leave the path unavailable for several polls and inspect `last_error`. Restore
   it and press Wake to verify that user actions bypass background retry delay.
6. Reload the integration and check for duplicate callbacks or reconnections after
   unloading it. If using a proxy, also check its stability over a longer session.
7. Restart HA with the droid powered off. The integration and Wake button should
   still load with Connected off. Turn the droid on and check that background
   recovery connects and delivers the pending startup wake. Repeat the HA restart
   with the droid already on to verify immediate startup connection/wake.
8. Let the droid fall asleep by itself. Asleep should turn on with
   `state_source: notification`; Connected can stay on if BLE remains connected.
   Press Wake and check that Asleep turns off immediately. If no sleep event is
   received, enable debug logging for `custom_components.sphero_r2d2_ble` and
   inspect the `R2-D2 power notification` messages.

## Maintaining and publishing

Run `python scripts/check_repository.py` for offline metadata/syntax checks. The
Validate workflow runs these checks, the regression suite, and the official HACS
and Hassfest actions. See [the HACS submission checklist](docs/HACS_SUBMISSION.md)
before publishing a release or requesting inclusion in the HACS default list.
