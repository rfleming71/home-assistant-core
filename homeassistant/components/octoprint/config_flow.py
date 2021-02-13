"""Config flow for OctoPrint integration."""
import logging

import requests
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_NAME,
    CONF_PATH,
    CONF_PORT,
    CONF_SSL,
)
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN  # pylint:disable=unused-import
from .octoprintapi import OctoPrintAPI

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "OctoPrint"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=80): cv.port,
        vol.Optional(CONF_PATH, default="/"): cv.string,
        vol.Optional(CONF_SSL, default=False): cv.boolean,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect."""

    protocol = "https" if data[CONF_SSL] else "http"
    base_url = f"{protocol}://{data[CONF_HOST]}:{data[CONF_PORT]}" f"{data[CONF_PATH]}"
    octoprint_api = OctoPrintAPI(
        base_url + "/api/",
        data[CONF_API_KEY],
        False,
        0,
    )
    if not await hass.async_add_executor_job(validate_connection, octoprint_api):
        _LOGGER.error("Failed to connect")
        raise CannotConnect

    # Return info that you want to store in the config entry.
    return {"title": data[CONF_NAME]}


def validate_connection(octoprint_api: OctoPrintAPI):
    """Validate the connection to the printer."""
    try:
        octoprint_api.get("job")
    except requests.exceptions.RequestException as conn_err:
        _LOGGER.error("Error setting up OctoPrint API: %r", conn_err)
        raise CannotConnect from conn_err

    return octoprint_api.job_available


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OctoPrint."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_import(self, user_input):
        """Handle import."""
        for entry in self._async_current_entries():
            if entry.data.get(CONF_HOST) == user_input[CONF_HOST]:
                return self.async_abort(reason="already_configured")

        return await self.async_step_user(user_input)


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
