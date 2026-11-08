"""Minimal, allowlisted diagnostics without addresses or arbitrary entry data."""

from dataclasses import asdict

from .coordinator import local_device
from .local_client import local_path


async def async_get_config_entry_diagnostics(hass, entry):
    """Read cached state only; downloading diagnostics never connects or writes."""
    coordinator = entry.runtime_data
    device = local_device(hass, coordinator.address)
    path = local_path(device)
    return {
        "entry": {
            "version": entry.version,
            "polling_disabled": entry.pref_disable_polling,
        },
        "connection": {
            "transport": "local_bluez_hci_monitor",
            "local_adapter": path.split("/")[3] if path else None,
            "device_visible_locally": device is not None,
            "proxy_supported": False,
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            # Exception text may contain an address or external library details.
            "last_exception_type": type(coordinator.last_exception).__name__
            if coordinator.last_exception
            else None,
            "confirmed_state": asdict(coordinator.data) if coordinator.data else None,
            "commands": coordinator.commands.attributes,
        },
    }
