"""Exercise the actual coordinator command method with minimal HA boundaries.

These are boundary unit tests, not a substitute for loading entities in HA.
Extracting the method allows testing its exception policy on Windows without
installing or mocking the entire Home Assistant runtime.
"""

import ast
import asyncio
import importlib
import logging
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

ROOT = Path(__file__).parents[1] / "custom_components/evonic_ble"
package = types.ModuleType("evonic_policy_test")
package.__path__ = [str(ROOT)]
sys.modules[package.__name__] = package
transport = importlib.import_module("evonic_policy_test.transport")
protocol = importlib.import_module("evonic_policy_test.protocol")


class HomeAssistantError(Exception):
    pass


class ServiceValidationError(HomeAssistantError):
    pass


class UpdateFailed(HomeAssistantError):
    pass


tree = ast.parse((ROOT / "coordinator.py").read_text())
coordinator = next(
    node
    for node in tree.body
    if isinstance(node, ast.ClassDef) and node.name == "EvonicCoordinator"
)
method = next(
    node
    for node in coordinator.body
    if isinstance(node, ast.AsyncFunctionDef) and node.name == "_perform_command"
)
namespace = dict(
    CommandRejected=transport.CommandRejected,
    HomeAssistantError=HomeAssistantError,
    ServiceValidationError=ServiceValidationError,
    UpdateFailed=UpdateFailed,
    asyncio=asyncio,
    _LOGGER=logging.getLogger("evonic_policy_tests"),
)
exec(compile(ast.Module(body=[method], type_ignores=[]), "coordinator.py", "exec"), namespace)


class CommandPolicyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        fixture = self

        class Coordinator:
            _perform_command = namespace["_perform_command"]

            async def async_command(self, **kwargs):
                # Test executor error policy directly; scheduler has separate tests.
                return await self._perform_command(kwargs, 1)

            def __init__(self):
                self.hass = object()
                self.available = True
                self.data = protocol.FireState(False, 0, 22, 2, 100)
                self.updated = []
                self.errors = []
                self._recovery_task = None
                self.transport = types.SimpleNamespace(execute=AsyncMock())
                self.async_request_refresh = AsyncMock(side_effect=self.recover)
                self.config_entry = types.SimpleNamespace(
                    async_create_background_task=self.create_task
                )

            def create_task(self, hass, coroutine, name):
                fixture.assertEqual(name, "Evonic BLE recovery status")
                return asyncio.create_task(coroutine)

            async def recover(self):
                self.available = True

            def async_set_updated_data(self, data):
                self.data = data
                self.available = True
                self.updated.append(data)

            def async_set_update_error(self, error):
                self.available = False
                self.errors.append(error)

        self.coordinator = Coordinator()

    async def test_off_brightness_rejection_keeps_available_and_publishes_fresh_state(self):
        c = self.coordinator
        state = c.data
        c.transport.execute.side_effect = transport.CommandRejected("Turn the fire on first", state)
        with self.assertRaises(ServiceValidationError):
            await c.async_command(brightness=60)
        self.assertTrue(c.available)
        self.assertEqual(c.updated, [state])
        self.assertEqual(c.errors, [])
        self.assertIsNone(c._recovery_task)
        c.transport.execute.assert_awaited_once_with(brightness=60)

    async def test_fresh_rejection_state_recovers_previous_unavailability(self):
        c = self.coordinator
        c.available = False
        c.transport.execute.side_effect = transport.CommandRejected("Fire off", c.data)
        with self.assertRaises(ServiceValidationError):
            await c.async_command(brightness=60)
        self.assertTrue(c.available)

    async def test_bad_input_does_not_claim_a_new_device_state(self):
        c = self.coordinator
        c.transport.execute.side_effect = transport.CommandRejected("Invalid percentage")
        with self.assertRaises(ServiceValidationError):
            await c.async_command(brightness=101)
        self.assertTrue(c.available)
        self.assertEqual(c.updated, [])
        self.assertEqual(c.errors, [])

    async def test_real_failure_marks_unavailable_then_requests_status_without_replay(self):
        c = self.coordinator
        c.transport.execute.side_effect = TimeoutError()
        with self.assertRaises(HomeAssistantError):
            await c.async_command(power=True)
        self.assertFalse(c.available)
        self.assertEqual(len(c.errors), 1)
        self.assertIn("TimeoutError", str(c.errors[0]))
        await c._recovery_task
        self.assertTrue(c.available)
        c.async_request_refresh.assert_awaited_once_with()
        c.transport.execute.assert_awaited_once_with(power=True)

    async def test_pending_recovery_is_not_duplicated(self):
        c = self.coordinator
        c.transport.execute.side_effect = TimeoutError()
        c._recovery_task = asyncio.get_running_loop().create_future()
        pending = c._recovery_task
        with self.assertRaises(HomeAssistantError):
            await c.async_command(power=True)
        self.assertIs(c._recovery_task, pending)
        c.async_request_refresh.assert_not_awaited()
        pending.cancel()

    async def test_cancel_is_not_converted_to_command_failure(self):
        c = self.coordinator
        c.transport.execute.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await c.async_command(power=True)
        self.assertEqual(c.errors, [])
        self.assertIsNone(c._recovery_task)

    async def test_success_publishes_confirmed_state(self):
        c = self.coordinator
        c.transport.execute.return_value = c.data
        await c.async_command(power=False)
        self.assertTrue(c.available)
        self.assertEqual(c.updated, [c.data])
        self.assertEqual(c.errors, [])


if __name__ == "__main__":
    unittest.main()
