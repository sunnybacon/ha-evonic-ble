"""Common fireplace entity metadata."""

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME


class EvonicEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            connections={(CONNECTION_BLUETOOTH, coordinator.address)},
            name=NAME,
            manufacturer="Evonic Fires",
        )

    @property
    def extra_state_attributes(self):
        # Queue state is internal. Publishing it here resets native controls to
        # the unchanged confirmed value while their service calls are pending.
        return {}
