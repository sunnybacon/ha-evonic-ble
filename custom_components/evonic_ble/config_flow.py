"""Manual configuration and a passive capability check before creating an entry."""

import re

import voluptuous as vol
from homeassistant import config_entries

from .const import DOMAIN, NAME
from .coordinator import local_device
from .hci import MonitorUnavailable, check_monitor_access


class EvonicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            address = user_input["address"].strip().upper()
            if not re.fullmatch(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}", address):
                errors["address"] = "invalid_address"
            else:
                await self.async_set_unique_id(address)
                self._abort_if_unique_id_configured()
                try:
                    await self.hass.async_add_executor_job(check_monitor_access)
                except MonitorUnavailable:
                    errors["base"] = "monitor_unavailable"
                else:
                    if local_device(self.hass, address) is None:
                        errors["base"] = "no_local_adapter"
                    else:
                        return self.async_create_entry(
                            title=NAME,
                            data={"address": address},
                        )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("address", default=(user_input or {}).get("address", "")): str,
                }
            ),
            errors=errors,
        )
