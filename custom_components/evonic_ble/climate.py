"""Main power, temperature and heat-level controls."""

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import ClimateEntityFeature, HVACMode
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.exceptions import HomeAssistantError

from .entity import EvonicEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([EvonicClimate(entry.runtime_data)])


class EvonicClimate(EvonicEntity, ClimateEntity):
    _attr_name = None
    _attr_translation_key = "fire"
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 5
    _attr_max_temp = 32
    _attr_target_temperature_step = 1
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_supported_features = (
        ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
        | ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
    )
    _attr_preset_modes = ["low", "high"]

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_climate"

    @property
    def hvac_mode(self):
        return HVACMode.HEAT if self.coordinator.data.power else HVACMode.OFF

    @property
    def native_target_temperature(self):
        return self.coordinator.data.target_temperature

    @property
    def native_current_temperature(self):
        return self.coordinator.data.room_temperature

    @property
    def preset_mode(self):
        return {1: "low", 2: "high"}.get(self.coordinator.data.heat_level)

    @property
    def extra_state_attributes(self):
        return {
            **super().extra_state_attributes,
            "heat_level": self.coordinator.data.heat_level,
            "controller_mode_raw": self.coordinator.data.schedule_mode,
        }

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode not in self.hvac_modes:
            raise HomeAssistantError("Only off and heat modes are supported")
        await self.coordinator.async_command(power=hvac_mode == HVACMode.HEAT)

    async def async_turn_on(self):
        await self.coordinator.async_command(power=True)

    async def async_turn_off(self):
        await self.coordinator.async_command(power=False)

    async def async_set_temperature(self, **kwargs):
        if ATTR_TEMPERATURE not in kwargs:
            raise HomeAssistantError("A target temperature is required")
        await self.coordinator.async_command(target=kwargs[ATTR_TEMPERATURE])

    async def async_set_preset_mode(self, preset_mode):
        if preset_mode not in ("low", "high"):
            raise HomeAssistantError("Heating preset is not available")
        await self.coordinator.async_command(level={"low": 1, "high": 2}[preset_mode])
