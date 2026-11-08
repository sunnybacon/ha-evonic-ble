"""Experimental local-adapter Evonic BLE integration."""

from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryError

from .coordinator import EvonicCoordinator
from .hci import MonitorUnavailable, check_monitor_access

PLATFORMS = [Platform.CLIMATE, Platform.NUMBER]


async def async_setup_entry(hass, entry):
    try:
        await hass.async_add_executor_job(check_monitor_access)
    except MonitorUnavailable as error:
        raise ConfigEntryError(str(error)) from error
    coordinator = EvonicCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()  # Query only. Never restore power.
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
