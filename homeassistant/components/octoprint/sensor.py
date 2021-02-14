"""Support for monitoring OctoPrint sensors."""
import logging

from pyoctoprintapi import OctoprintApi
import requests

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, PERCENTAGE, TEMP_CELSIUS, TIME_SECONDS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity

from .const import DOMAIN as COMPONENT_DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_devices
):
    """Set up the available OctoPrint binary sensors."""
    octoprint_api: OctoprintApi = hass.data[COMPONENT_DOMAIN][config_entry.entry_id]
    devices = []
    sensor_name = config_entry.data[CONF_NAME]
    try:
        printer_info = await octoprint_api.get_printer_info()
        types = ["actual", "target"]
        for tool in printer_info["temperature"]:
            for temp_type in types:
                devices.append(
                    OctoPrintTemperatureSensor(
                        octoprint_api, sensor_name, tool, temp_type
                    )
                )
    except BaseException as ex:
        _LOGGER.error("Error getting printering information %s", ex)

    devices.append(OctoPrintStatusSensor(octoprint_api, sensor_name))
    devices.append(OctoPrintJobPercentageSensor(octoprint_api, sensor_name))
    devices.append(OctoPrintTimeRemainingSensor(octoprint_api, sensor_name))
    devices.append(OctoPrintTimeElapsedSensor(octoprint_api, sensor_name))

    async_add_devices(devices, True)
    return True


class OctoPrintSensorBase(Entity):
    """Representation of an OctoPrint sensor."""

    def __init__(self, api: OctoprintApi, sensor_name: str, sensor_type: str):
        """Initialize a new OctoPrint sensor."""
        self._api = api
        self._state = None
        self._sensor_name = sensor_name
        self._name = f"{sensor_name} {sensor_type}"

    @property
    def device_info(self):
        """Device info."""
        return {
            "identifiers": {(COMPONENT_DOMAIN, self._api._base_url)},
        }

    @property
    def unique_id(self):
        """Return a unique id."""
        return f"{self._name}-{self._api._base_url}"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        if self.unit_of_measurement in (PERCENTAGE, TEMP_CELSIUS):
            if not self._state:
                return 0
            return round(self._state, 2)

        return self._state


class OctoPrintStatusSensor(OctoPrintSensorBase):
    """Representation of an OctoPrint sensor."""

    def __init__(self, api: OctoprintApi, sensor_name: str):
        """Initialize a new OctoPrint sensor."""
        super().__init__(api, sensor_name, "Current State")
        _LOGGER.debug("Created OctoPrint temperature sensor %r", self)

    async def async_update(self):
        """Update state of sensor."""
        try:
            info = await self._api.get_printer_info()
            self._state = info["state"]["text"]
        except requests.exceptions.ConnectionError as ex:
            _LOGGER.error(ex)
            return

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return "mdi:printer-3d"


class OctoPrintJobPercentageSensor(OctoPrintSensorBase):
    """Representation of an OctoPrint sensor."""

    def __init__(self, api: OctoprintApi, sensor_name: str):
        """Initialize a new OctoPrint sensor."""
        super().__init__(api, sensor_name, "Job Percentage")
        _LOGGER.debug("Created OctoPrint temperature sensor %r", self)

    async def async_update(self):
        """Update state of sensor."""
        try:
            info = await self._api.get_job_info()
            self._state = info["progress"]["completion"]
        except requests.exceptions.ConnectionError as ex:
            _LOGGER.error(ex)
            return

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return PERCENTAGE

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return "mdi:file-percent"


class OctoPrintTimeRemainingSensor(OctoPrintSensorBase):
    """Representation of an OctoPrint sensor."""

    def __init__(self, api: OctoprintApi, sensor_name: str):
        """Initialize a new OctoPrint sensor."""
        super().__init__(api, sensor_name, "Time Remaining")
        _LOGGER.debug("Created OctoPrint temperature sensor %r", self)

    async def async_update(self):
        """Update state of sensor."""
        try:
            info = await self._api.get_job_info()
            self._state = info["progress"]["printTimeLeft"]
        except requests.exceptions.ConnectionError as ex:
            _LOGGER.error(ex)
            return

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return TIME_SECONDS

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return "mdi:clock-start"


class OctoPrintTimeElapsedSensor(OctoPrintSensorBase):
    """Representation of an OctoPrint sensor."""

    def __init__(self, api: OctoprintApi, sensor_name: str):
        """Initialize a new OctoPrint sensor."""
        super().__init__(api, sensor_name, "Time Elapsed")
        _LOGGER.debug("Created OctoPrint sensor %r", self)

    async def async_update(self):
        """Update state of sensor."""
        try:
            info = await self._api.get_job_info()
            self._state = info["progress"]["printTime"]
        except requests.exceptions.ConnectionError as ex:
            _LOGGER.error(ex)
            return

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return TIME_SECONDS

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return "mdi:clock-end"


class OctoPrintTemperatureSensor(OctoPrintSensorBase):
    """Representation of an OctoPrint sensor."""

    def __init__(self, api: OctoprintApi, sensor_name: str, tool: str, temp_type: str):
        """Initialize a new OctoPrint sensor."""
        super().__init__(api, sensor_name, f"{temp_type} {tool} temp")
        self._temp_type = temp_type
        self._api_tool = tool
        self._state = 0
        _LOGGER.debug("Created OctoPrint temperature sensor %r", self)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return TEMP_CELSIUS

    async def async_update(self):
        """Update state of sensor."""
        try:
            info = await self._api.get_printer_info()
            self._state = info["temperature"][self._api_tool][self._temp_type]
        except requests.exceptions.ConnectionError as ex:
            _LOGGER.error(ex)
            return
