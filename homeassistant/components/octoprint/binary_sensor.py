"""Support for monitoring OctoPrint binary sensors."""
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
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
    coordinator = hass.data[COMPONENT_DOMAIN][config_entry.entry_id]["coordinator"]
    device_id = hass.data[COMPONENT_DOMAIN][config_entry.entry_id]["device_id"]

    devices = [
        OctoPrintPrintingBinarySensor(
            coordinator, device_id, config_entry.data[CONF_NAME]
        ),
        OctoPrintPrintingErrorBinarySensor(
            coordinator, device_id, config_entry.data[CONF_NAME]
        ),
    ]

    async_add_devices(devices, True)
    return True


class OctoPrintBinarySensorBase(CoordinatorEntity, BinarySensorEntity):
    """Representation an OctoPrint binary sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        device_id: str,
        sensor_name: str,
        sensor_type: str,
    ):
        """Initialize a new OctoPrint sensor."""
        super().__init__(coordinator)
        self.sensor_name = sensor_name
        self._name = f"{sensor_name} {sensor_type}"
        self.sensor_type = sensor_type
        self.device_id = device_id
        _LOGGER.debug("Created OctoPrint binary sensor %r", self)

    @property
    def device_info(self):
        """Device info."""
        return {
            "identifiers": {(COMPONENT_DOMAIN, self.device_id)},
            "name": self.sensor_name,
        }

    @property
    def unique_id(self):
        """Return a unique id."""
        return f"{self._name}-{self.sensor_name}"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def device_class(self):
        """Return the class of this sensor, from DEVICE_CLASSES."""
        return None


class OctoPrintPrintingBinarySensor(OctoPrintBinarySensorBase):
    """Representation an OctoPrint binary sensor."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, device_id: str, sensor_name: str
    ):
        """Initialize a new OctoPrint sensor."""
        super().__init__(coordinator, device_id, sensor_name, "Printing")

    @property
    def is_on(self):
        """Return true if binary sensor is on."""
        state = self.coordinator.data["printer"]
        if not state:
            return None

        return bool(state["state"]["flags"]["printing"])


class OctoPrintPrintingErrorBinarySensor(OctoPrintBinarySensorBase):
    """Representation an OctoPrint binary sensor."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, device_id: str, sensor_name: str
    ):
        """Initialize a new OctoPrint sensor."""
        super().__init__(coordinator, device_id, sensor_name, "Printing Error")

    @property
    def is_on(self):
        """Return true if binary sensor is on."""
        state = self.coordinator.data["printer"]
        if not state:
            return None

        return bool(state["state"]["flags"]["error"])
