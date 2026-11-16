# Remaining work

Current baseline: beta.1, tested with one legacy Evonic BLE controller on a
Raspberry Pi running Home Assistant 2026.11.1.

## Testing to complete

- [ ] Record at least 48 hours of ordinary use after beta.1, checking temperature
  dropouts, recovery and resource use.
- [ ] Test radio loss during a control write and its confirmation.
- [ ] Test loss of the Bluetooth adapter, range loss and a Pi reboot.
- [ ] Unload the integration during an active command and check cleanup.
- [ ] Test restoring a previous version's files.
- [ ] Add tests using the real Home Assistant lifecycle and service framework.
- [ ] Arrange an independent human code review if the project gains wider use.

Results already recorded are in [testing](docs/TESTING.md). Live heating tests
need someone present to observe the fire and restore its previous settings.

## Ongoing maintenance

- Check the local Bluetooth workaround after HA or Bluetooth-library upgrades.
- Record other controller models and temperature accuracy if they are tested.
- Investigate controller mode 182 if support for native schedules is pursued.

## Deferred or outside the current scope

- Further touchscreen testing: connection was intermittent, and the owner
  doesn't plan to use it.
- Bluetooth proxies: these need a different transport.
- Schedule editing.

The current controls and beta.1 fixes are described in the [README](README.md)
and [changelog](CHANGELOG.md).
