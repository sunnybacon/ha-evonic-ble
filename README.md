![Evonic Fires](custom_components/evonic_ble/brand/logo.png)

# Evonic BLE for Home Assistant

Control an older Bluetooth-only Evonic BLE / E-Touch fire from Home Assistant.
Works locally, without a cloud account. This integration is separate from
Evonic's Wi-Fi products.

I built this for my own fire. I'm a Home Assistant power user with some coding
experience, and developed it with help from OpenAI Codex. It has been tested
with one controller on a Raspberry Pi; support for other models is unconfirmed.
This is an unofficial personal project, currently in beta.

## Controls

- **Climate:** Heat / Off, room temperature, target temperature (5–32°C) and
  Low / High presets.
- **Brightness:** 0–100% through a number entity.

Turn the fire on before changing brightness, target temperature or heat level.
Room temperature is checked about once a minute, including while Off, provided
mains power is available. Heat mode means the fire is enabled; it doesn't report
whether the heating element is currently running. Schedule editing isn't supported.

## Requirements

- A local Linux Bluetooth adapter accessible to Home Assistant, with HCI monitor
  access. This works on the tested Raspberry Pi. **Bluetooth proxies aren't supported.**
- The fire powered at the mains and within Bluetooth range.
- Phone apps and the touchscreen disconnected while Home Assistant controls it.

## Install through Marketplace

1. Add `https://github.com/sunnybacon/ha-evonic-ble` as a custom repository,
   category **Integration**.
2. Enable prereleases and download **Evonic BLE**.
3. Restart Home Assistant.
4. Open **Settings → Devices & Services → Add Integration → Evonic BLE** and
   enter the fire's Bluetooth address.

For updates, install the new version through Marketplace and restart. Keep your
existing integration entry. See [installation](docs/INSTALLATION.md) for manual
installation, moving an existing install to Marketplace and rollback.

## Things to know

Commands can take a few seconds to confirm. Failed commands aren't automatically
repeated; recovery checks the fire's status. Suspect temperature readings may
show as unknown while the other controls remain available.

The fire may resume its previous On state when mains power returns. Home
Assistant doesn't turn it on during startup or reconnection. Removing the
integration doesn't switch the physical fire off.

## More information

- [Troubleshooting and diagnostics](docs/TROUBLESHOOTING.md)
- [Device behaviour and Bluetooth workaround](docs/BEHAVIOUR.md)
- [Testing](docs/TESTING.md), [code review](CODE_REVIEW.md) and [remaining work](REMAINING_WORK.md)
- [Changelog](CHANGELOG.md) and [releases](https://github.com/sunnybacon/ha-evonic-ble/releases)
- [Report an issue](https://github.com/sunnybacon/ha-evonic-ble/issues) — omit credentials,
  private device addresses and raw captures.

Not affiliated with Evonic Fires or Home Assistant. Source code is [MIT licensed](LICENSE);
manufacturer artwork has separate [attribution](docs/BRANDING.md) and [ownership](NOTICE).
