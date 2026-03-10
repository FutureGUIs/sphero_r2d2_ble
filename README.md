# Sphero R2-D2 BLE custom integration

This custom integration converts the BLE command logic from `r2d2_ha_tiny.ino` into a native Home Assistant Bluetooth integration.

## Included features

- Config flow with automatic Bluetooth discovery
- Native BLE connection through Home Assistant Bluetooth adapters and proxies
- Wake and sleep buttons
- Animation select entity plus play-animation button
- Battery, connected, and asleep entities
- Stance select entity (`bipod` / `tripod`)
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
