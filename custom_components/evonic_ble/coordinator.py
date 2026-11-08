"""HA adapter selection and confirmed state updates."""

import asyncio
import logging
from datetime import timedelta

from bleak_retry_connector import establish_connection
from homeassistant.components import bluetooth
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .commands import CommandScheduler, RequestRejected
from .const import NAME
from .local_client import LocalOnlyClient, local_path
from .transport import CommandRejected, EvonicTransport, validate_request

_LOGGER = logging.getLogger(__name__)


def local_device(hass, address):
    # Select only local BlueZ entries, even if a proxy has stronger RSSI.
    for candidate in bluetooth.async_scanner_devices_by_address(hass, address, connectable=True):
        device = candidate.ble_device
        if local_path(device):
            return device
    return None


class EvonicCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(
            hass,
            _LOGGER,
            name=NAME,
            config_entry=entry,
            update_interval=timedelta(seconds=60),
            always_update=False,
        )
        self.address = entry.data["address"]
        self._recovery_task = None
        self.commands = CommandScheduler(
            self._perform_command,
            self._command_status_changed,
            lambda coroutine: entry.async_create_background_task(
                hass, coroutine, "Evonic BLE controls", eager_start=False
            ),
        )

        async def connect(device):
            return await establish_connection(
                LocalOnlyClient,
                device,
                NAME,
                max_attempts=2,
                use_services_cache=False,
                evonic_path=local_path(device),
            )

        self.transport = EvonicTransport(
            self.address, lambda: local_device(hass, self.address), connect
        )

    def _command_status_changed(self):
        # Do not notify the control entities for queue-only changes. Confirmed
        # results and availability errors still publish through the coordinator.
        _LOGGER.debug("Fire command queue: %s", self.commands.attributes)

    async def _async_update_data(self):
        try:
            # A poll cannot publish an older state in the middle of a control burst.
            await self.commands.wait_idle()
            return await self.transport.execute()
        except Exception as error:
            _LOGGER.debug("Status read failed: %s: %s", type(error).__name__, error)
            raise UpdateFailed(f"Unable to read fire: {type(error).__name__}: {error}") from error

    async def async_command(self, **kwargs):
        try:
            validate_request(**kwargs)
            return await self.commands.submit(**kwargs)
        except (RequestRejected, CommandRejected) as error:
            raise ServiceValidationError(str(error)) from error

    async def _perform_command(self, values, timeout):  # noqa: ASYNC109 - enforces the scheduler's remaining budget
        _LOGGER.debug("Fire control starting: %s", values)
        try:
            async with asyncio.timeout(timeout):
                state = await self.transport.execute(**values)
        except CommandRejected as error:
            if error.state is not None:
                # The fire answered successfully, but this action is inapplicable.
                self.async_set_updated_data(error.state)
            raise ServiceValidationError(str(error)) from error
        except Exception as error:
            # The write may have happened. Do not retain an available old state.
            self.async_set_update_error(UpdateFailed(f"{type(error).__name__}: {error}"))
            # Read only; never replay the failed mutation. Entry unload cancels it.
            if self._recovery_task is None or self._recovery_task.done():
                self._recovery_task = self.config_entry.async_create_background_task(
                    self.hass, self.async_request_refresh(), "Evonic BLE recovery status"
                )
            raise HomeAssistantError(f"Fire command was not confirmed: {error}") from error
        self.async_set_updated_data(state)
        _LOGGER.debug("Fire control confirmed: %s", values)
        return state

    async def async_shutdown(self):
        await self.commands.close()
        await super().async_shutdown()
