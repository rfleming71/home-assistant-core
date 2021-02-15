"""Support for monitoring OctoPrint sensors."""
import logging

from pyoctoprintapi import OctoprintClient

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, PERCENTAGE, TEMP_CELSIUS, TIME_SECONDS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN as COMPONENT_DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_devices
):
    """Set up the available OctoPrint binary sensors."""
    client: OctoprintClient = hass.data[COMPONENT_DOMAIN][config_entry.entry_id][
        "client"
    ]
    coordinator: DataUpdateCoordinator = hass.data[COMPONENT_DOMAIN][
        config_entry.entry_id
    ]["coordinator"]
    device_id: str = hass.data[COMPONENT_DOMAIN][config_entry.entry_id]["device_id"]
    devices = []
    sensor_name = config_entry.data[CONF_NAME]
    try:
        printer_info = await client.get_printer_info()
        types = ["actual", "target"]
        for tool in printer_info.temperatures:
            for temp_type in types:
                devices.append(
                    OctoPrintTemperatureSensor(
                        coordinator, device_id, sensor_name, tool.name, temp_type
                    )
                )
    except BaseException as ex:
        _LOGGER.error("Error getting printering information %s", ex)

    devices.append(OctoPrintStatusSensor(coordinator, device_id, sensor_name))
    devices.append(OctoPrintJobPercentageSensor(coordinator, device_id, sensor_name))
    devices.append(OctoPrintTimeRemainingSensor(coordinator, device_id, sensor_name))
    devices.append(OctoPrintTimeElapsedSensor(coordinator, device_id, sensor_name))

    async_add_devices(devices, True)
    return True


class OctoPrintSensorBase(CoordinatorEntity, Entity):
    """Representation of an OctoPrint sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        device_id: str,
        sensor_name: str,
        sensor_type: str,
    ):
        """Initialize a new OctoPrint sensor."""
        super().__init__(coordinator)
        self._state = None
        self._sensor_name = sensor_name
        self._name = f"{sensor_name} {sensor_type}"
        self._device_id = device_id

    @property
    def device_info(self):
        """Device info."""
        return {
            "identifiers": {(COMPONENT_DOMAIN, self._device_id)},
        }

    @property
    def unique_id(self):
        """Return a unique id."""
        return f"{self._name}-{self._device_id}"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name


class OctoPrintStatusSensor(OctoPrintSensorBase):
    """Representation of an OctoPrint sensor."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, device_id: str, sensor_name: str
    ):
        """Initialize a new OctoPrint sensor."""
        super().__init__(coordinator, device_id, sensor_name, "Current State")
        _LOGGER.debug("Created OctoPrint temperature sensor %r", self)

    @property
    def state(self):
        """Return sensor state."""
        printer = self.coordinator.data["printer"]
        if not printer:
            return None

        return printer.state.text

    @property
    def icon(self):
        """Icon to use in the frontend."""
        return "mdi:printer-3d"


class OctoPrintJobPercentageSensor(OctoPrintSensorBase):
    """Representation of an OctoPrint sensor."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, device_id: str, sensor_name: str
    ):
        """Initialize a new OctoPrint sensor."""
        super().__init__(coordinator, device_id, sensor_name, "Job Percentage")
        _LOGGER.debug("Created OctoPrint temperature sensor %r", self)

    @property
    def state(self):
        """Return sensor state."""
        job = self.coordinator.data["job"]
        if not job:
            return 0

        state = job.progress.completion
        if not state:
            return 0

        return round(state, 2)

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

    def __init__(
        self, coordinator: DataUpdateCoordinator, device_id: str, sensor_name: str
    ):
        """Initialize a new OctoPrint sensor."""
        super().__init__(coordinator, device_id, sensor_name, "Time Remaining")
        _LOGGER.debug("Created OctoPrint temperature sensor %r", self)

    @property
    def state(self):
        """Return sensor state."""
        job = self.coordinator.data["job"]
        if not job:
            return None

        return job.progress.print_time_left

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

    def __init__(
        self, coordinator: DataUpdateCoordinator, device_id: str, sensor_name: str
    ):
        """Initialize a new OctoPrint sensor."""
        super().__init__(coordinator, device_id, sensor_name, "Time Elapsed")
        _LOGGER.debug("Created OctoPrint sensor %r", self)

    @property
    def state(self):
        """Return sensor state."""
        job = self.coordinator.data["job"]
        if not job:
            return None

        return job.progress.print_time

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

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        device_id: str,
        sensor_name: str,
        tool: str,
        temp_type: str,
    ):
        """Initialize a new OctoPrint sensor."""
        super().__init__(
            coordinator, device_id, sensor_name, f"{temp_type} {tool} temp"
        )
        self._temp_type = temp_type
        self._api_tool = tool
        self._state = 0
        _LOGGER.debug("Created OctoPrint temperature sensor %r", self)

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return TEMP_CELSIUS

    @property
    def state(self):
        """Return sensor state."""
        printer = self.coordinator.data["printer"]
        if not printer:
            return None

        for temp in printer.temperatures:
            if temp.name == self._api_tool:
                return round(temp._raw[self._temp_type], 2)

        return None
