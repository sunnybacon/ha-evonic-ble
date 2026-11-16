# Installation and updates

## Marketplace

Add `https://github.com/sunnybacon/ha-evonic-ble` as a custom repository with
category **Integration**. Enable prereleases to see beta releases, download
Evonic BLE and restart Home Assistant. Then add Evonic BLE under
**Settings → Devices & Services**, entering the fire's Bluetooth address.

Close the manufacturer's apps and disconnect the touchscreen first. Assign the
device to its room after setup. No YAML configuration is needed.

The project isn't listed in the default Marketplace catalog. Current downloads
are on the [releases page](https://github.com/sunnybacon/ha-evonic-ble/releases).

## Moving a manual install to Marketplace

Back up `custom_components/evonic_ble` before updating. Add the repository and
download through Marketplace, then restart HA. Keep the existing Devices &
Services entry so its device, entities and settings can be retained.

This migration was tested on the owner's HA 2026.11.1 installation with alpha.16:
the entry, device, entity IDs and area were retained, and polling resumed.

## Manual installation

1. Back up an existing `custom_components/evonic_ble` folder before replacing it.
2. Copy the release's `custom_components/evonic_ble` folder, including `brand`
   and `translations`, into HA's `custom_components` directory.
3. Restart Home Assistant.
4. Add Evonic BLE under **Settings → Devices & Services** if this is a new install.

Development dependencies, phone captures and APK files aren't needed on HA.
Standard dashboard cards for climate and number entities can control the fire;
no project-specific dashboard or JavaScript patch is required.

## Rollback and removal

Keep a copy of the previous integration folder and note its version. To roll
back, restore that folder and restart HA. A file-version rollback trial is still
on the testing checklist.

Disabling or removing the integration doesn't switch the physical fire off.
Use the appliance's own controls first if needed. When uninstalling manually,
remove only `custom_components/evonic_ble`, never HA's configuration directory.
