"""Brightness belongs to the same device; no separate light entity."""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.exceptions import HomeAssistantError

from .entity import EvonicEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([EvonicBrightness(entry.runtime_data)])


class EvonicBrightness(EvonicEntity, NumberEntity):
    _attr_name = "Brightness"
    _attr_icon = "mdi:brightness-6"
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "%"
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_brightness"

    @property
    def native_value(self):
        return self.coordinator.data.brightness

    async def async_set_native_value(self, value):
        if type(value) not in (int, float) or not 0 <= value <= 100 or int(value) != value:
            raise HomeAssistantError("Brightness must be a whole percentage")
        await self.coordinator.async_command(brightness=int(value))
