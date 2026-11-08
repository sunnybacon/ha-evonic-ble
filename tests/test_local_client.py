"""HA route-adapter boundary tests; remote routes must never be allocated."""

import ast
import asyncio
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from bleak.backends import BleakBackend

PATH = "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_01"
ADDRESS = "AA:BB:CC:DD:EE:01"


class FakeHaClient:
    def __init__(self, device, *args, **kwargs):
        self.backend_id = BleakBackend.BLUEZ_DBUS
        self.disconnected = False

    def _async_get_best_available_backend_and_device(self, manager):
        raise AssertionError("Global/remote-capable selector must not be called")

    def _async_get_backend_for_ble_device(self, manager, scanner, device):
        manager.allocations.append(device)
        return manager.result

    async def connect(self, **kwargs):
        pass

    async def disconnect(self):
        self.disconnected = True


fake_ha = types.ModuleType("habluetooth")
fake_ha.HaBleakClientWrapper = FakeHaClient
spec = importlib.util.spec_from_file_location(
    "evonic_local_test", Path(__file__).parents[1] / "custom_components/evonic_ble/local_client.py"
)
local = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"habluetooth": fake_ha}):
    spec.loader.exec_module(local)


def device(path=PATH, **details):
    return types.SimpleNamespace(address=ADDRESS, details={"path": path, **details})


def backend(device_value=None, source=None, module="bleak.backends.bluezdbus.client"):
    return types.SimpleNamespace(
        device=device_value or device(),
        source=source,
        client=type("Backend", (), {"__module__": module}),
    )


class Manager:
    def __init__(self, devices, result):
        self.devices = devices
        self.result = result
        self.allocations = []
        self.released = []

    def async_scanner_devices_by_address(self, address, connectable):
        return [types.SimpleNamespace(ble_device=value, scanner=object()) for value in self.devices]

    def async_release_connection_slot(self, device):
        self.released.append(device)


class LocalRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_connection_factory_requires_fresh_services_and_local_route(self):
        tree = ast.parse(
            (Path(__file__).parents[1] / "custom_components/evonic_ble/coordinator.py").read_text()
        )
        cls = next(
            n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EvonicCoordinator"
        )
        init = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
        connect = next(
            n for n in init.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "connect"
        )
        establish = AsyncMock(return_value=object())
        scope = dict(
            establish_connection=establish,
            LocalOnlyClient=local.LocalOnlyClient,
            local_path=local.local_path,
            NAME="Evonic BLE",
        )
        exec(compile(ast.Module(body=[connect], type_ignores=[]), "coordinator.py", "exec"), scope)
        selected = device()
        await scope["connect"](selected)
        establish.assert_awaited_once_with(
            local.LocalOnlyClient,
            selected,
            "Evonic BLE",
            max_attempts=2,
            use_services_cache=False,
            evonic_path=PATH,
        )

    def client(self):
        return local.LocalOnlyClient(device(), evonic_path=PATH)

    async def test_proxy_first_and_another_local_adapter_are_never_allocated(self):
        other = device(PATH.replace("hci0", "hci1"))
        proxy = device(source="remote-proxy")
        selected = device()
        manager = Manager([proxy, other, selected], backend(selected))
        client = self.client()
        result = client._async_get_best_available_backend_and_device(manager)
        self.assertIs(result, manager.result)
        self.assertEqual(manager.allocations, [selected])
        self.assertEqual(manager.released, [])

    async def test_local_failure_never_falls_back_to_proxy(self):
        selected = device()
        proxy = device(source="remote-proxy")
        manager = Manager([selected, proxy], None)
        with self.assertRaises(local.LocalRouteError):
            self.client()._async_get_best_available_backend_and_device(manager)
        self.assertEqual(manager.allocations, [selected])

    async def test_only_proxy_or_wrong_adapter_fails_before_allocation(self):
        for devices in ([device(source="proxy")], [device(PATH.replace("hci0", "hci1"))], []):
            manager = Manager(devices, backend())
            with self.assertRaises(local.LocalRouteError):
                self.client()._async_get_best_available_backend_and_device(manager)
            self.assertEqual(manager.allocations, [])

    async def test_wrong_backend_releases_slot_and_is_rejected(self):
        for result in (
            backend(source="proxy"),
            backend(module="bleak_esphome.backend.client"),
            backend(device(PATH.replace("hci0", "hci1"))),
            types.SimpleNamespace(),
        ):
            selected = device()
            manager = Manager([selected], result)
            with self.assertRaises(local.LocalRouteError):
                self.client()._async_get_best_available_backend_and_device(manager)
            self.assertEqual(manager.released, [selected])

    async def test_retry_cannot_change_original_adapter(self):
        with self.assertRaises(local.LocalRouteError):
            local.LocalOnlyClient(device(PATH.replace("hci0", "hci1")), evonic_path=PATH)

    async def test_changed_ha_selector_api_fails_closed(self):
        with patch.object(FakeHaClient, "_async_get_best_available_backend_and_device", None):
            with self.assertRaises(local.LocalRouteError):
                self.client()
        with patch.object(FakeHaClient, "_async_get_backend_for_ble_device", None):
            with self.assertRaises(local.LocalRouteError):
                self.client()

    async def test_backend_identity_guard_disconnects_remote_before_return(self):
        client = self.client()
        client.backend_id = "BleakClientESPHome"
        with self.assertRaises(local.LocalRouteError):
            await client.connect()
        self.assertTrue(client.disconnected)

    async def test_bluez_backend_identity_is_accepted(self):
        client = self.client()
        await client.connect()
        self.assertFalse(client.disconnected)

    async def test_defensive_backend_rejection_disconnects_before_raising(self):
        client = self.client()
        client.backend_id = None
        with self.assertRaises(local.LocalRouteError):
            await client.connect()
        self.assertTrue(client.disconnected)

    async def test_cancel_during_rejected_backend_cleanup_stays_cancelled(self):
        client = self.client()
        client.backend_id = None
        client.disconnect = AsyncMock(side_effect=asyncio.CancelledError())
        with self.assertRaises(asyncio.CancelledError):
            await client.connect()
        client.disconnect.assert_awaited_once_with()

    async def test_rejected_backend_cleanup_failure_keeps_reason_and_cause(self):
        client = self.client()
        client.backend_id = None
        error = OSError("disconnect failed")
        client.disconnect = AsyncMock(side_effect=error)
        with self.assertRaisesRegex(local.LocalRouteError, "cleanup failed") as result:
            await client.connect()
        self.assertIs(result.exception.__cause__, error)

    async def test_bad_or_remote_details_are_not_local(self):
        for value in (
            None,
            types.SimpleNamespace(details=None),
            device(source="remote"),
            device("/org/bluez/hci0/not_a_device"),
            device("/other/path"),
        ):
            self.assertIsNone(local.local_path(value))


if __name__ == "__main__":
    unittest.main()
