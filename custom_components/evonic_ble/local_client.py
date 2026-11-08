"""Isolate the HA wrapper's route selector for this local-HCI-only device.

HA reselects the backend at connect time, ignoring the original BLEDevice route.
There is no per-client pin argument in the inspected wrapper implementation.
This intentionally overrides one protected selector, retaining HA allocation,
tracking and cleanup. Check compatibility and fail closed; never patch globals.
"""

import asyncio
import logging
import re

from bleak.backends import BleakBackend
from habluetooth import HaBleakClientWrapper

_LOGGER = logging.getLogger(__name__)


class LocalRouteError(RuntimeError):
    """A local-only route cannot be guaranteed."""


def local_path(device) -> str | None:
    details = getattr(device, "details", None)
    if not isinstance(details, dict) or details.get("source"):
        return None
    path = details.get("path")
    if not isinstance(path, str) or not re.fullmatch(
        r"/org/bluez/hci\d+/dev_(?:[0-9A-Fa-f]{2}_){5}[0-9A-Fa-f]{2}", path
    ):
        return None
    return path


class LocalOnlyClient(HaBleakClientWrapper):
    """Never select a remote route, including after local connection failures."""

    def __init__(self, device, *args, evonic_path: str, **kwargs):
        if not callable(
            getattr(HaBleakClientWrapper, "_async_get_best_available_backend_and_device", None)
        ):
            raise LocalRouteError(
                "HA Bluetooth route selector changed; local-only routing is unavailable"
            )
        if not callable(getattr(self, "_async_get_backend_for_ble_device", None)):
            raise LocalRouteError(
                "HA Bluetooth backend allocator changed; local-only routing is unavailable"
            )
        if local_path(device) != evonic_path:
            raise LocalRouteError("Connection retry changed the selected local adapter")
        self._evonic_path = evonic_path
        self._evonic_address = device.address
        super().__init__(device, *args, **kwargs)

    def _async_get_best_available_backend_and_device(self, manager):
        # Do NOT call the base selector: it ranks all scanners, including proxies.
        for candidate in manager.async_scanner_devices_by_address(self._evonic_address, True):
            device = candidate.ble_device
            if local_path(device) != self._evonic_path or device.address != self._evonic_address:
                continue
            backend = self._async_get_backend_for_ble_device(manager, candidate.scanner, device)
            if backend is None:
                raise LocalRouteError(
                    "Selected local Bluetooth adapter has no free connection slot"
                )
            if (
                not hasattr(backend, "source")
                or backend.source
                or local_path(getattr(backend, "device", None)) != self._evonic_path
                or getattr(getattr(backend, "client", None), "__module__", "")
                != "bleak.backends.bluezdbus.client"
            ):
                manager.async_release_connection_slot(device)
                raise LocalRouteError("HA returned an unsupported backend for the local adapter")
            adapter = self._evonic_path.split("/")[3]
            _LOGGER.debug("Selected local adapter %s; proxy fallback disabled", adapter)
            return backend
        raise LocalRouteError("Fire is not visible on the selected local Bluetooth adapter")

    async def connect(self, **kwargs):
        await super().connect(**kwargs)
        if self.backend_id != BleakBackend.BLUEZ_DBUS:
            # Defence in depth if HA changes how it invokes the selector.
            try:
                await self.disconnect()
            except asyncio.CancelledError:
                raise
            except Exception as error:
                raise LocalRouteError(
                    "Refusing fire commands through a non-BlueZ backend; disconnect cleanup failed"
                ) from error
            raise LocalRouteError("Refusing fire commands through a non-BlueZ backend")
