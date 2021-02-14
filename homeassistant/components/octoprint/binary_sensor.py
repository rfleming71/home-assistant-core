"""Support for monitoring OctoPrint binary sensors."""
import logging

from pyoctoprintapi import OctoprintApi
import requests

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant

from .const import DOMAIN as COMPONENT_DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_devices
):
    """Set up the available OctoPrint binary sensors."""
    octoprint_api = hass.data[COMPONENT_DOMAIN][config_entry.entry_id]

    devices = [
        OctoPrintPrintingBinarySensor(octoprint_api, config_entry.data[CONF_NAME]),
        OctoPrintPrintingErrorBinarySensor(octoprint_api, config_entry.data[CONF_NAME]),
    ]

    async_add_devices(devices, True)
    return True


class OctoPrintBinarySensorBase(BinarySensorEntity):
    """Representation an OctoPrint binary sensor."""

    def __init__(self, api: OctoprintApi, sensor_name: str, sensor_type: str):
        """Initialize a new OctoPrint sensor."""
        self.sensor_name = sensor_name
        self._name = f"{sensor_name} {sensor_type}"
        self.sensor_type = sensor_type
        self.api = api
        self._state = False
        _LOGGER.debug("Created OctoPrint binary sensor %r", self)

    @property
    def device_info(self):
        """Device info."""
        return {
            "identifiers": {(COMPONENT_DOMAIN, self.api._base_url)},
        }

    @property
    def unique_id(self):
        """Return a unique id."""
        return f"{self._name}-{self.api._base_url}"

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


class OctoPrintPrintingBinarySensor(OctoPrintBinarySensorBase):
    """Representation an OctoPrint binary sensor."""

    def __init__(self, api: OctoprintApi, sensor_name: str):
        """Initialize a new OctoPrint sensor."""
        super().__init__(api, sensor_name, "Printing")

    async def async_update(self):
        """Update state of sensor."""
        try:
            info = await self.api.get_printer_info()
            self._state = info["state"]["flags"]["printing"]
        except requests.exceptions.ConnectionError:
            # Error calling the api, already logged in api.update()
            return


class OctoPrintPrintingErrorBinarySensor(OctoPrintBinarySensorBase):
    """Representation an OctoPrint binary sensor."""

    def __init__(self, api: OctoprintApi, sensor_name: str):
        """Initialize a new OctoPrint sensor."""
        super().__init__(api, sensor_name, "Printing Error")

    async def async_update(self):
        """Update state of sensor."""
        try:
            info = await self.api.get_printer_info()
            self._state = info["state"]["flags"]["error"]
        except requests.exceptions.ConnectionError:
            # Error calling the api, already logged in api.update()
            return
