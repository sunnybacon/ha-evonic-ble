"""Exercise the actual climate adapter methods with thin HA boundary stand-ins."""

import ast
import types
import unittest
from enum import IntFlag, StrEnum
from pathlib import Path
from unittest.mock import AsyncMock

ROOT = Path(__file__).parents[1] / "custom_components/evonic_ble"


class Feature(IntFlag):
    TARGET_TEMPERATURE = 1
    PRESET_MODE = 16
    TURN_ON = 128
    TURN_OFF = 256


class Mode(StrEnum):
    OFF = "off"
    HEAT = "heat"


class HomeAssistantError(Exception):
    pass


class BaseEntity:
    def __init__(self, coordinator):
        self.coordinator = coordinator

    @property
    def extra_state_attributes(self):
        return {}


class ClimateEntity:
    @property
    def hvac_modes(self):
        return self._attr_hvac_modes


tree = ast.parse((ROOT / "climate.py").read_text())
class_node = next(node for node in tree.body if isinstance(node, ast.ClassDef))
scope = dict(
    EvonicEntity=BaseEntity,
    ClimateEntity=ClimateEntity,
    ClimateEntityFeature=Feature,
    HVACMode=Mode,
    UnitOfTemperature=types.SimpleNamespace(CELSIUS="°C"),
    ATTR_TEMPERATURE="temperature",
    HomeAssistantError=HomeAssistantError,
)
exec(compile(ast.Module(body=[class_node], type_ignores=[]), "climate.py", "exec"), scope)
EvonicClimate = scope["EvonicClimate"]


class ClimateControls(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.coordinator = types.SimpleNamespace(
            address="00:11:22:33:44:55",
            async_command=AsyncMock(),
            data=types.SimpleNamespace(
                power=False,
                target_temperature=22,
                heat_level=1,
                schedule_mode=0,
                room_temperature=20.4,
            ),
        )

    async def test_current_temperature_is_measurement_even_while_off(self):
        entity = EvonicClimate(self.coordinator)
        self.assertEqual(entity.native_current_temperature, 20.4)
        self.assertEqual(entity.native_target_temperature, 22)
        self.assertEqual(entity.hvac_mode, Mode.OFF)
        self.coordinator.data.room_temperature = None
        self.assertIsNone(entity.native_current_temperature)

    async def test_temperature_action_does_not_request_power_on(self):
        entity = EvonicClimate(self.coordinator)
        await entity.async_set_temperature(temperature=23)
        self.coordinator.async_command.assert_awaited_once_with(target=23)

    async def test_heat_presets_map_to_recovered_gear_values(self):
        entity = EvonicClimate(self.coordinator)
        await entity.async_set_preset_mode("high")
        await entity.async_set_preset_mode("low")
        self.assertEqual(
            [call.kwargs for call in self.coordinator.async_command.await_args_list],
            [{"level": 2}, {"level": 1}],
        )

    async def test_all_heating_controls_are_standard(self):
        entity = EvonicClimate(self.coordinator)
        self.assertEqual(
            entity._attr_supported_features,
            Feature.TURN_ON | Feature.TURN_OFF | Feature.TARGET_TEMPERATURE | Feature.PRESET_MODE,
        )
        self.assertEqual(entity._attr_preset_modes, ["low", "high"])
        self.assertNotIn("heating_controls_experimental", entity.extra_state_attributes)

    async def test_existing_opt_out_entries_still_get_standard_controls(self):
        setup = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef))
        scope = {"EvonicClimate": EvonicClimate}
        exec(compile(ast.Module(body=[setup], type_ignores=[]), "climate.py", "exec"), scope)
        for data, options in (
            ({}, {}),
            ({"heating_controls": False}, {}),
            ({"heating_controls": True}, {"heating_controls": False}),
        ):
            entities = []
            entry = types.SimpleNamespace(runtime_data=self.coordinator, data=data, options=options)
            await scope["async_setup_entry"](None, entry, entities.extend)
            self.assertEqual(len(entities), 1)
            await entities[0].async_set_temperature(temperature=23)
            await entities[0].async_set_preset_mode("low")
        self.assertEqual(self.coordinator.async_command.await_count, 6)

    async def test_invalid_preset_and_missing_temperature_send_no_command(self):
        entity = EvonicClimate(self.coordinator)
        with self.assertRaises(HomeAssistantError):
            await entity.async_set_preset_mode("off")
        with self.assertRaises(HomeAssistantError):
            await entity.async_set_temperature()
        self.coordinator.async_command.assert_not_awaited()

    async def test_reported_target_and_preset_are_device_state(self):
        entity = EvonicClimate(self.coordinator)
        self.assertEqual(entity.native_target_temperature, 22)
        self.assertEqual(entity.preset_mode, "low")
        self.assertEqual(entity.hvac_mode, Mode.OFF)
        self.assertNotIn("command_pending", entity.extra_state_attributes)
        self.assertEqual(entity.extra_state_attributes["heat_level"], 1)
        self.coordinator.data.schedule_mode = 182
        self.assertEqual(entity.extra_state_attributes["controller_mode_raw"], 182)

    async def test_power_action_is_independent_of_heat_setters(self):
        entity = EvonicClimate(self.coordinator)
        await entity.async_set_hvac_mode(Mode.OFF)
        self.coordinator.async_command.assert_awaited_once_with(power=False)


if __name__ == "__main__":
    unittest.main()
