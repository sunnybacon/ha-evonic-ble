"""Diagnostics must not expose arbitrary config or cause Bluetooth operations."""

import ast
import types
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import Mock

from test_transport import protocol


class DiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        tree = ast.parse(
            (Path(__file__).parents[1] / "custom_components/evonic_ble/diagnostics.py").read_text()
        )
        function = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef))
        self.local_device = Mock(return_value=object())
        self.local_path = Mock(return_value="/org/bluez/hci0/dev_PRIVATE_ADDRESS")
        scope = dict(
            asdict=asdict,
            local_device=self.local_device,
            local_path=self.local_path,
        )
        exec(compile(ast.Module(body=[function], type_ignores=[]), "diagnostics.py", "exec"), scope)
        self.read = scope["async_get_config_entry_diagnostics"]
        self.entry = types.SimpleNamespace(
            version=1,
            pref_disable_polling=False,
            data={"address": "PRIVATE_ADDRESS", "unexpected_token": "TOP_SECRET"},
            runtime_data=types.SimpleNamespace(
                address="PRIVATE_ADDRESS",
                last_update_success=True,
                last_exception=None,
                data=protocol.FireState(False, 0, 23, 2, 100, 20.5),
                commands=types.SimpleNamespace(attributes={"command_pending": False}),
            ),
        )

    async def test_allowlist_omits_addresses_secrets_and_preserves_useful_state(self):
        result = await self.read(object(), self.entry)
        self.assertNotIn("PRIVATE_ADDRESS", repr(result))
        self.assertNotIn("TOP_SECRET", repr(result))
        self.assertEqual(result["connection"]["local_adapter"], "hci0")
        self.assertEqual(result["coordinator"]["confirmed_state"]["room_temperature"], 20.5)
        self.assertEqual(result["coordinator"]["commands"], {"command_pending": False})
        self.assertNotIn("heating_controls_enabled", result["entry"])
        self.local_device.assert_called_once()

    async def test_failure_is_useful_without_leaking_exception_text(self):
        self.local_device.return_value = None
        self.local_path.return_value = None
        self.entry.runtime_data.last_update_success = False
        self.entry.runtime_data.last_exception = TimeoutError("PRIVATE_ADDRESS TOP_SECRET")
        self.entry.runtime_data.data = None
        result = await self.read(object(), self.entry)
        self.assertNotIn("PRIVATE_ADDRESS", repr(result))
        self.assertNotIn("TOP_SECRET", repr(result))
        self.assertEqual(result["coordinator"]["last_exception_type"], "TimeoutError")
        self.assertIsNone(result["coordinator"]["confirmed_state"])
        self.assertFalse(result["connection"]["device_visible_locally"])
