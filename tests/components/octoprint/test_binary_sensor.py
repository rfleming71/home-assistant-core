"""The tests for Octoptint binary sensor module."""
import logging
from unittest import mock

from pyoctoprintapi import OctoprintPrinterInfo

from homeassistant.components.octoprint import binary_sensor as sensor
from homeassistant.components.octoprint.const import DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def test_setup_config(hass):
    """Test component setup."""
    api = mock.MagicMock()
    hass.data[DOMAIN] = {"foo": api}

    add_entities = mock.MagicMock()
    config_entry = mock.MagicMock()
    config_entry.entry_id = "foo"
    config_entry.data = {"host": "http://192.168.1.35/", "name": "name"}

    assert await sensor.async_setup_entry(hass, config_entry, add_entities)

    await hass.async_block_till_done()
    assert add_entities.call_count == 1


def test_OctoPrintPrintingBinarySensor_properties(hass):
    """Test the properties."""
    coordinator = DataUpdateCoordinator(hass, _LOGGER, name="octoprint-test")
    coordinator.data = {"printer": {}}
    test_sensor = sensor.OctoPrintPrintingBinarySensor(
        coordinator, "device_id", "OctoPrint"
    )
    assert "OctoPrint Printing" == test_sensor.name
    assert "OctoPrint Printing-device_id" == test_sensor.unique_id
    assert not test_sensor.device_class
    assert {("octoprint", "device_id")} == test_sensor.device_info["identifiers"]


def test_OctoPrintPrintingErrorBinarySensor_properties(hass):
    """Test the properties."""
    coordinator = DataUpdateCoordinator(hass, _LOGGER, name="octoprint-test")
    coordinator.data = {"printer": {}}
    test_sensor = sensor.OctoPrintPrintingErrorBinarySensor(
        coordinator, "device_id", "OctoPrint"
    )
    assert "OctoPrint Printing Error" == test_sensor.name
    assert "OctoPrint Printing Error-device_id" == test_sensor.unique_id
    assert not test_sensor.device_class
    assert {("octoprint", "device_id")} == test_sensor.device_info["identifiers"]


def test_OctoPrintPrintingBinarySensor_is_on(hass):
    """Test the is_on property."""
    coordinator = DataUpdateCoordinator(hass, _LOGGER, name="octoprint-test")
    coordinator.data = {
        "printer": OctoprintPrinterInfo(
            {
                "state": {
                    "flags": {
                        "printing": True,
                    },
                    "text": "Operational",
                },
                "temperature": [],
            }
        )
    }
    test_sensor = sensor.OctoPrintPrintingBinarySensor(
        coordinator, "device_id", "OctoPrint"
    )
    assert STATE_ON == test_sensor.state

    coordinator.data = {
        "printer": OctoprintPrinterInfo(
            {
                "state": {
                    "flags": {
                        "printing": False,
                    },
                    "text": "Operational",
                },
                "temperature": [],
            }
        )
    }
    assert STATE_OFF == test_sensor.state


def test_OctoPrintPrintingErrorBinarySensor_is_on(hass):
    """Test the is_on property."""
    coordinator = DataUpdateCoordinator(hass, _LOGGER, name="octoprint-test")
    coordinator.data = {
        "printer": OctoprintPrinterInfo(
            {
                "state": {
                    "flags": {
                        "error": True,
                    },
                    "text": "Operational",
                },
                "temperature": [],
            }
        )
    }
    test_sensor = sensor.OctoPrintPrintingErrorBinarySensor(
        coordinator, "device_id", "OctoPrint"
    )
    assert STATE_ON == test_sensor.state

    coordinator.data = {
        "printer": OctoprintPrinterInfo(
            {
                "state": {
                    "flags": {
                        "error": False,
                    },
                    "text": "Operational",
                },
                "temperature": [],
            }
        )
    }
    assert STATE_OFF == test_sensor.state
