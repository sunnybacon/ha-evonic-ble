![Evonic Fires](custom_components/evonic_ble/brand/logo.png)

# Evonic BLE for Home Assistant

An **unofficial, local, early-development** custom integration for the older
Bluetooth-only Evonic BLE / E-Touch fireplace controller. This is separate from
Evonic's Wi-Fi products and integrations. No cloud account is required.

## Why this exists

This began as a personal project because I own an Evonic BLE fire and wanted to
control it from Home Assistant. I am an experienced Home Assistant power user
with some coding experience, rather than an experienced integration developer.
I developed this with help from OpenAI Codex, working iteratively: investigating
the protocol, implementing changes, reviewing failures and testing against my
own fire.

AI assistance is part of the project's history, not evidence that the code is
correct. Automated checks and observed device tests are recorded separately,
along with their limits. Compatibility has been demonstrated with **one
controller on a Raspberry Pi running Home Assistant 2026.11.0**. Broader hardware
compatibility and long-term reliability remain unproven. This is a personal
project with no commitment to support every Evonic model.

It is not made, endorsed or supported by Evonic Fires or Home Assistant.
Official artwork identifies the compatible product; see [attribution](docs/BRANDING.md).

## Controls

| Entity | Available functions |
| --- | --- |
| Climate | Heat / Off; measured room temperature; reported target temperature |
| Climate settings | Target temperature, 5–32 °C in 1 °C steps; Low / High presets |
| Brightness number | 0–100%, while the fire is on |

Target temperature and Low / High are standard controls, available by default.
They have passed live control/readback tests on the owner's fire; this does not
establish compatibility with every other controller. The previous experimental
checkbox is removed; existing entries need no reconfiguration.

Heat means the fire is enabled; it does not prove the element is actively
heating. There is no invented `hvac_action`, independent light entity, schedule
editor, clock setting or firmware updater.

Brightness, target and heat-level changes require the fire to be on; they never
implicitly turn it on. Room temperature continues polling while Off if mains
power is available. Status polling is approximately once a minute while entities
are subscribed; a dashboard need not be open.

## Requirements and installation

- A local Linux Bluetooth adapter visible inside HA Core, with Linux HCI monitor
  socket access. This has worked on the tested Pi.
- The fire powered at the mains and within Bluetooth range.
- Native phone apps and touchscreen disconnected while HA needs access.

**Bluetooth proxies are not supported by the current transport.** Ordinary BLE
support alone does not guarantee monitor permission. The integration checks
access and does not change system permissions automatically.

This is an early public build, version `0.1.0-alpha.16`. It is available as a
custom repository; it has not been submitted to the default Marketplace catalog.

For Marketplace installation, add `https://github.com/sunnybacon/ha-evonic-ble`
as a custom repository with category **Integration**, then download Evonic BLE.
Enable pre-release versions if installing an alpha release. Restart HA when
Marketplace requests it, then add Evonic BLE in Devices & Services.

If Evonic BLE is already installed manually, back up its folder first, add the
custom repository and download it through Marketplace. Keep the existing
Devices & Services entry; do not delete and recreate it. Restart HA after the
download. Using the same integration domain and existing entry should preserve
the device, entity IDs and settings. This migration was verified on the owner's
HA 2026.11.1 installation with release `0.1.0-alpha.16`: the existing entry,
device, entity IDs and area were retained, and room-temperature polling resumed
after restart. This does not establish every installation or rollback path.

For manual installation:

1. Back up an existing `custom_components/evonic_ble` folder before updating.
2. Copy this project's `custom_components/evonic_ble` folder, including `brand`
   and `translations`, into HA's `custom_components` directory.
3. Restart HA after replacing an already loaded version. For a first install,
   restart if the new integration is not discovered.
4. Open **Settings → Devices & Services → Add Integration → Evonic BLE** and
   enter the fire's Bluetooth address. Close the manufacturer's apps first.
5. Assign the device to its room. All listed controls are included by default.

No `configuration.yaml` entry, research APK, captures or development dependencies
are needed on HA. Entity IDs depend on the local entity registry. Any standard
dashboard supporting climate and number entities can control this integration;
the author's personal dashboard and JavaScript patches are not required.

## Behaviour to know

Commands are serialized and checked against fresh device status. Rapid
brightness changes retain the latest waiting value; explicit Off takes priority
over waiting brightness. Uncertain commands are reported rather than silently
accepted. Recovery reads status and **does not replay control writes**. The
card can take a few seconds to reflect a physically confirmed change.

The integration does not restore saved power at startup or reconnection. The
appliance itself resumed its previous On state after mains restoration in one
trial, so restoring mains can leave the fire on independently of HA.

Changing target temperature selects manual mode, as the native app does, and
can leave a native timing mode. Low / High preserves recognized modes. Unknown
modes are retained, but heater-setting writes are guarded. See [behaviour](docs/BEHAVIOUR.md).

## Help and development

- [Troubleshooting and diagnostics](docs/TROUBLESHOOTING.md)
- [Test results, limits and development checks](docs/TESTING.md)
- [Remaining work](REMAINING_WORK.md) and [focused code review](CODE_REVIEW.md)
- [Change history](CHANGELOG.md)
- [Branding](docs/BRANDING.md) and [Marketplace release checklist](docs/RELEASE_READINESS.md)

The code checkpoint is `0.1.0-alpha.16`: 95 offline tests and Ruff checks passed,
alongside specific observed control/recovery trials. These are not a full HA
test suite, independent audit or reliability guarantee. Ordinary use can
continue while remaining failure cases and soak testing are tracked.

## Updating and rollback

Keep a copy of the previous integration folder and note its version. To roll
back, restore that folder and restart HA. Disabling/removing the integration
does not switch the physical fire off; use its own controls first if necessary.
Remove only this integration's folder when uninstalling, never HA's config
directory. Idle unload/re-enable and startup recovery have been tested; a
file-version rollback trial remains outstanding.

Source code and original documentation are provided under the [MIT licence](LICENSE).
Manufacturer artwork has separate ownership; see [NOTICE](NOTICE) and
[branding attribution](docs/BRANDING.md). Report reproducible problems through
[GitHub Issues](https://github.com/sunnybacon/ha-evonic-ble/issues), excluding
private addresses, credentials and raw phone/HA captures.
