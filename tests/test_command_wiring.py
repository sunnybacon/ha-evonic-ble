"""Wire the real HA-facing command methods to the real scheduler/executor.

HA entity rendering and the Bluetooth radio still need separate live tests.
"""

import ast
import asyncio
import logging
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from test_command_policy import (
    HomeAssistantError,
    ServiceValidationError,
    UpdateFailed,
    protocol,
    transport,
)
from test_commands import commands

tree = ast.parse(
    (Path(__file__).parents[1] / "custom_components/evonic_ble/coordinator.py").read_text()
)
coordinator = next(
    node
    for node in tree.body
    if isinstance(node, ast.ClassDef) and node.name == "EvonicCoordinator"
)
methods = [
    node
    for node in coordinator.body
    if isinstance(node, ast.AsyncFunctionDef)
    and node.name in ("async_command", "_perform_command", "_async_update_data")
]
scope = dict(
    asyncio=asyncio,
    _LOGGER=logging.getLogger("evonic_wiring_tests"),
    CommandRejected=transport.CommandRejected,
    validate_request=transport.validate_request,
    RequestRejected=commands.RequestRejected,
    ServiceValidationError=ServiceValidationError,
    HomeAssistantError=HomeAssistantError,
    UpdateFailed=UpdateFailed,
)
exec(compile(ast.Module(body=methods, type_ignores=[]), "coordinator.py", "exec"), scope)


class WiringTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        fixture = self
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.calls = []

        class Coordinator:
            async_command = scope["async_command"]
            _perform_command = scope["_perform_command"]
            _async_update_data = scope["_async_update_data"]

            def __init__(self):
                self.data = protocol.FireState(True, 0, 22, 2, 100)
                self.available = True
                self.confirmed_values = []
                self.hass = object()
                self._recovery_task = None
                self.async_request_refresh = AsyncMock()
                self.config_entry = types.SimpleNamespace(
                    async_create_background_task=lambda hass, task, name: asyncio.create_task(task)
                )
                self.transport = types.SimpleNamespace(execute=self.execute)
                self.commands = commands.CommandScheduler(
                    self._perform_command, lambda: None, asyncio.create_task
                )

            async def execute(self, **values):
                fixture.calls.append(values)
                if len(fixture.calls) == 1:
                    fixture.started.set()
                    await fixture.release.wait()
                if "brightness" in values:
                    self.data = protocol.FireState(True, 0, 22, 2, values["brightness"])
                return self.data

            def async_set_updated_data(self, state):
                self.data = state
                self.available = True
                self.confirmed_values.append(state.brightness)

            def async_set_update_error(self, error):
                self.available = False

        self.coordinator = Coordinator()

    async def asyncTearDown(self):
        await self.coordinator.commands.close()

    async def test_end_to_end_coalescing_keeps_confirmed_state_separate(self):
        c = self.coordinator
        first = asyncio.create_task(c.async_command(brightness=40))
        await self.started.wait()
        middle = asyncio.create_task(c.async_command(brightness=50))
        latest = asyncio.create_task(c.async_command(brightness=70))
        await asyncio.sleep(0)
        self.assertEqual(c.data.brightness, 100)
        self.assertEqual(c.commands.attributes["pending_brightness"], 70)
        self.release.set()
        await asyncio.gather(first, middle, latest)
        self.assertEqual(self.calls, [{"brightness": 40}, {"brightness": 70}])
        self.assertEqual(c.confirmed_values, [40, 70])
        self.assertFalse(c.commands.busy)

    async def test_invalid_value_cannot_replace_a_valid_pending_value(self):
        c = self.coordinator
        first = asyncio.create_task(c.async_command(brightness=40))
        await self.started.wait()
        latest = asyncio.create_task(c.async_command(brightness=70))
        await asyncio.sleep(0)
        with self.assertRaises(ServiceValidationError):
            await c.async_command(brightness=101)
        self.assertEqual(c.commands.attributes["pending_brightness"], 70)
        self.release.set()
        await asyncio.gather(first, latest)
        self.assertEqual(c.confirmed_values, [40, 70])

    async def test_poll_waits_until_latest_control_is_confirmed(self):
        c = self.coordinator
        first = asyncio.create_task(c.async_command(brightness=40))
        await self.started.wait()
        poll = asyncio.create_task(c._async_update_data())
        latest = asyncio.create_task(c.async_command(brightness=70))
        await asyncio.sleep(0)
        self.assertFalse(poll.done())
        self.release.set()
        await asyncio.gather(first, latest, poll)
        self.assertEqual(self.calls, [{"brightness": 40}, {"brightness": 70}, {}])
        self.assertEqual(poll.result().brightness, 70)

    async def test_total_executor_timeout_marks_uncertain_and_schedules_readback(self):
        c = self.coordinator
        c.commands.operation_timeout = 0.02
        with self.assertRaises(HomeAssistantError):
            await c.async_command(brightness=40)
        await c._recovery_task
        self.assertFalse(c.available)
        c.async_request_refresh.assert_awaited_once_with()
        self.assertFalse(c.commands.busy)

    async def _interrupted_command(self, *, queued_off):
        c = self.coordinator
        actual = c.data
        self.calls.clear()
        availability = []
        initial_error = c.async_set_update_error

        def mark_error(error):
            initial_error(error)
            availability.append(c.available)

        c.async_set_update_error = mark_error

        async def execute(**values):
            nonlocal actual
            self.calls.append(dict(values))
            if values == {"brightness": 40}:
                # Hardware applies the change, then the response is lost.
                actual = protocol.FireState(True, 0, 22, 2, 40)
                self.started.set()
                await self.release.wait()
                raise ConnectionError("Link lost during confirmation")
            if values == {"power": False}:
                actual = protocol.FireState(False, 0, 22, 2, actual.brightness)
            return actual

        async def refresh():
            state = await c._async_update_data()
            c.async_set_updated_data(state)

        c.transport.execute = execute
        c.async_request_refresh = AsyncMock(side_effect=refresh)
        active = asyncio.create_task(c.async_command(brightness=40))
        await self.started.wait()
        pending = asyncio.create_task(
            c.async_command(**({"power": False} if queued_off else {"brightness": 70}))
        )
        await asyncio.sleep(0)
        self.assertEqual(c.data.brightness, 100)  # No optimistic result.
        self.release.set()
        results = await asyncio.gather(active, pending, return_exceptions=True)
        self.assertIsInstance(results[0], HomeAssistantError)
        await c._recovery_task
        self.assertEqual(availability, [False])
        self.assertTrue(c.available)
        self.assertFalse(c.commands.busy)
        self.assertEqual(c.data, actual)
        self.assertEqual(c.data.brightness, 40)
        c.async_request_refresh.assert_awaited_once_with()
        if queued_off:
            self.assertFalse(c.data.power)
            self.assertFalse(isinstance(results[1], Exception))
            self.assertEqual(self.calls, [{"brightness": 40}, {"power": False}, {}])
        else:
            self.assertIsInstance(results[1], ServiceValidationError)
            self.assertEqual(self.calls, [{"brightness": 40}, {}])

    async def test_lost_confirmation_discards_queued_brightness_and_recovers_by_query(self):
        await self._interrupted_command(queued_off=False)

    async def test_lost_confirmation_preserves_explicit_queued_off_before_recovery_query(self):
        await self._interrupted_command(queued_off=True)
