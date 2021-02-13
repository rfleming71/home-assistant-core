"""Support for monitoring OctoPrint binary sensors."""
import logging

import requests

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from .const import DOMAIN as COMPONENT_DOMAIN
from .octoprintapi import OctoPrintAPI

BINARY_SENSOR_TYPES = {
    # API Endpoint, Group, Key, unit
    "Printing": ["printer", "state", "printing", None],
    "Printing Error": ["printer", "state", "error", None],
}

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_devices
):
    """Set up the available OctoPrint binary sensors."""
    octoprint_api = hass.data[COMPONENT_DOMAIN][config_entry.entry_id]

    devices = [
        OctoPrintBinarySensor(
            octoprint_api,
            octo_type,
            BINARY_SENSOR_TYPES[octo_type][2],
            config_entry.data[CONF_NAME],
            BINARY_SENSOR_TYPES[octo_type][3],
            BINARY_SENSOR_TYPES[octo_type][0],
            BINARY_SENSOR_TYPES[octo_type][1],
            "flags",
        )
        for octo_type in BINARY_SENSOR_TYPES
    ]

    async_add_devices(devices, True)
    return True


class OctoPrintBinarySensor(BinarySensorEntity):
    """Representation an OctoPrint binary sensor."""

    def __init__(
        self,
        api: OctoPrintAPI,
        condition,
        sensor_type,
        sensor_name,
        unit,
        endpoint,
        group,
        tool=None,
    ):
        """Initialize a new OctoPrint sensor."""
        self.sensor_name = sensor_name
        if tool is None:
            self._name = f"{sensor_name} {condition}"
        else:
            self._name = f"{sensor_name} {condition}"
        self.sensor_type = sensor_type
        self.api = api
        self._state = False
        self._unit_of_measurement = unit
        self.api_endpoint = endpoint
        self.api_group = group
        self.api_tool = tool
        _LOGGER.debug("Created OctoPrint binary sensor %r", self)

    @property
    def device_info(self):
        """Device info."""
        return {
            "identifiers": {(COMPONENT_DOMAIN, self.api.api_url)},
        }

    @property
    def unique_id(self):
        """Return a unique id."""
        return f"{self._name}-{self.api.api_url}"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def is_on(self):
        """Return true if binary sensor is on."""
        return bool(self._state)

    @property
    def device_class(self):
        """Return the class of this sensor, from DEVICE_CLASSES."""
        return None

    def update(self):
        """Update state of sensor."""
        try:
            self._state = self.api.update(
                self.sensor_type, self.api_endpoint, self.api_group, self.api_tool
            )
        except requests.exceptions.ConnectionError:
            # Error calling the api, already logged in api.update()
            return
