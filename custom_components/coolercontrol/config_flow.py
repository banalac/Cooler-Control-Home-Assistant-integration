"""Config flow for CoolerControl."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import HomeAssistantError

from .api import CoolerControlApiClient, CoolerControlApiError, CoolerControlAuthError
from .const import (
    CONF_TOKEN,
    CONF_VERIFY_SSL,
    DEFAULT_PORT,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_TOKEN): str,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    }
)


async def _validate_input(hass, data: dict[str, Any]) -> None:
    session = async_get_clientsession(hass, verify_ssl=data[CONF_VERIFY_SSL])
    client = CoolerControlApiClient(
        session,
        data[CONF_HOST],
        data[CONF_PORT],
        data[CONF_TOKEN],
        verify_ssl=data[CONF_VERIFY_SSL],
    )
    await client.async_verify()


class CoolerControlConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CoolerControl."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            unique_id = f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            try:
                await _validate_input(self.hass, user_input)
            except CoolerControlAuthError:
                errors["base"] = "invalid_auth"
            except CoolerControlApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error validating CoolerControl connection")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"CoolerControl ({user_input[CONF_HOST]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
