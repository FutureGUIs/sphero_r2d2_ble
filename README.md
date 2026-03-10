# Sphero R2-D2 BLE custom integration

This custom integration converts the BLE command logic from `r2d2_ha_tiny.ino` into a native Home Assistant Bluetooth integration.

## Included features

- Config flow for entering the R2-D2 Bluetooth MAC address
- Native BLE connection through Home Assistant Bluetooth adapters / proxies
- Wake and sleep buttons
- Animation select entity plus play-animation button
- Battery, RSSI, connected, asleep, and idle-time entities
- Stance select entity (`bipod` / `tripod`)
- `sphero_r2d2_ble.play_animation` service
- `sphero_r2d2_ble.set_stance` service

## Install

1. Unzip into `config/custom_components/`
2. Restart Home Assistant
3. Add **Sphero R2-D2 BLE** from **Settings → Devices & Services → Add Integration**
4. Enter the Bluetooth MAC address for the droid

## Notes

- The command packet builder, UUIDs, auth string, wake/sleep/animation/stance commands, and battery read are translated from the referenced `.ino` sketch.
- Animations use IDs `0..56` to match the sketch README.
- The toy must be reachable by a Home Assistant Bluetooth adapter or ESPHome Bluetooth proxy.
