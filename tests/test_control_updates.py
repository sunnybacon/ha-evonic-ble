"""Actual coordinator wiring must not publish queue-only control updates."""

import ast
import asyncio
import logging
import types
import unittest
from datetime import timedelta
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

ROOT = Path(__file__).parents[1] / "custom_components/evonic_ble"


class BaseCoordinator:
    def __init__(self, hass, logger, **kwargs):
        self.hass = hass
        self.config_entry = kwargs["config_entry"]
        self.notifications = []
        self.data = protocol.FireState(False, 0, 22, 2, 100)

    def async_update_listeners(self):
        self.notifications.append(("listener", self.data))

    def async_set_updated_data(self, data):
        self.data = data
        self.notifications.append(("confirmed", data))

    def async_set_update_error(self, error):
        self.notifications.append(("unavailable", error))

    async def async_request_refresh(self):
        pass


class ControlUpdates(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.started, self.release = asyncio.Event(), asyncio.Event()

        async def execute(**kwargs):
            self.started.set()
            await self.release.wait()
            return protocol.FireState(True, 0, 23, 1, 60)

        self.execute = AsyncMock(side_effect=execute)
        tree = ast.parse((ROOT / "coordinator.py").read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        scope = dict(
            DataUpdateCoordinator=BaseCoordinator,
            timedelta=timedelta,
            asyncio=asyncio,
            _LOGGER=logging.getLogger(__name__),
            NAME="Test",
            CommandScheduler=commands.CommandScheduler,
            EvonicTransport=lambda *a: types.SimpleNamespace(execute=self.execute),
            RequestRejected=commands.RequestRejected,
            CommandRejected=transport.CommandRejected,
            validate_request=transport.validate_request,
            ServiceValidationError=ServiceValidationError,
            HomeAssistantError=HomeAssistantError,
            UpdateFailed=UpdateFailed,
        )
        exec(compile(ast.Module(body=[cls], type_ignores=[]), "coordinator.py", "exec"), scope)
        entry = types.SimpleNamespace(
            data={"address": "00:11:22:33:44:55"},
            async_create_background_task=lambda hass, coro, name, **kw: asyncio.create_task(coro),
        )
        self.c = scope["EvonicCoordinator"](object(), entry)

    async def asyncTearDown(self):
        await self.c.commands.close()
        if self.c._recovery_task:
            await self.c._recovery_task

    async def test_all_control_types_publish_only_after_confirmation(self):
        for values in ({"power": True}, {"level": 1}, {"target": 23}, {"brightness": 60}):
            with self.subTest(values=values):
                self.started.clear()
                self.release.clear()
                self.c.notifications.clear()
                before = self.c.data
                task = asyncio.create_task(self.c.async_command(**values))
                await self.started.wait()
                self.assertTrue(self.c.commands.busy)
                self.assertEqual(self.c.notifications, [])
                self.assertIs(self.c.data, before)
                self.release.set()
                await task
                self.assertFalse(self.c.commands.busy)
                self.assertEqual([x[0] for x in self.c.notifications], ["confirmed"])
        self.assertEqual(self.execute.await_count, 4)

    async def test_failure_still_publishes_unavailable(self):
        self.execute.side_effect = OSError("connection lost")
        with self.assertRaises(HomeAssistantError):
            await self.c.async_command(power=True)
        self.assertEqual([x[0] for x in self.c.notifications], ["unavailable"])
        self.assertFalse(self.c.commands.busy)


class EntityPresentation(unittest.TestCase):
    def test_entity_has_no_queue_attributes_and_number_has_fixed_icon(self):
        tree = ast.parse((ROOT / "entity.py").read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        scope = dict(CoordinatorEntity=object)
        exec(compile(ast.Module(body=[cls], type_ignores=[]), "entity.py", "exec"), scope)
        entity = scope["EvonicEntity"].__new__(scope["EvonicEntity"])
        entity.coordinator = types.SimpleNamespace(
            commands=types.SimpleNamespace(busy=True, attributes={"command_pending": True})
        )
        self.assertEqual(entity.extra_state_attributes, {})
        tree = ast.parse((ROOT / "number.py").read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
        scope.update(
            NumberEntity=type("NumberEntity", (), {}),
            NumberMode=types.SimpleNamespace(SLIDER="slider"),
        )
        exec(compile(ast.Module(body=[cls], type_ignores=[]), "number.py", "exec"), scope)
        self.assertNotIn("icon", scope["EvonicBrightness"].__dict__)
        self.assertEqual(scope["EvonicBrightness"]._attr_icon, "mdi:brightness-6")
