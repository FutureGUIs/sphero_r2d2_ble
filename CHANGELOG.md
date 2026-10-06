# Changelog

## 0.3.0

- Load entities while the droid is powered off or unreachable. Attempt the initial
  connection/wake in the background and retry with bounded backoff.
- Publish BLE disconnects immediately and ignore callbacks from old connections.
- Respect intentional sleep by suspending polling and automatic reconnection.
- Detect automatic sleep from validated Sphero power notifications.
- Reconnect and wake before Play Animation, with a short wake delay.
- Add a Nearby diagnostic sensor, communication/battery timestamps, connection
  errors, and the source of the Asleep state.
- Report required handshake failures and bound GATT operations with timeouts.
- Prevent queued actions or polls from reconnecting after unload.
- Add hardware-free regression tests, HACS/Hassfest CI, and submission metadata.
- Remove tracked Python bytecode and ignore generated caches.

## 0.2.0

- Existing integration baseline with Bluetooth discovery, animations, wake/sleep,
  stance, LEDs, head positioning, and battery diagnostics.
