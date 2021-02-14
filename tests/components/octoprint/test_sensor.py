"""The tests for Octoptint binary sensor module."""
import logging
from unittest import mock

from homeassistant.components.octoprint import sensor
from homeassistant.components.octoprint.const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def test_setup_config(hass):
    """Test component setup."""
    api = mock.MagicMock()
    hass.data[DOMAIN] = {"foo": api}

    add_entities = mock.MagicMock()
    config_entry = mock.MagicMock()
    config_entry.entry_id = "foo"
    config_entry.data = {
        "host": "http://192.168.1.35/",
        "name": "name",
        "sensors": ["Printing"],
    }
    assert await sensor.async_setup_entry(hass, config_entry, add_entities)
    await hass.async_block_till_done()

    assert add_entities.call_count == 1


def test_properties():
    """Test the properties."""
    api = mock.MagicMock()
    api.api_url = "http://192.168.1.35/path/api"
    test_sensor = sensor.OctoPrintSensor(
        api, "condition", "sensor_type", "name", "unit", "job", "group"
    )
    assert "name condition" == test_sensor.name
    assert "name condition-http://192.168.1.35/path/api" == test_sensor.unique_id
    assert not test_sensor.device_class
    assert {("octoprint", "http://192.168.1.35/path/api")} == test_sensor.device_info[
        "identifiers"
    ]


def test_properties_with_tool():
    """Test the properties."""
    api = mock.MagicMock()
    api.api_url = "http://192.168.1.35/path/api"
    test_sensor = sensor.OctoPrintSensor(
        api, "condition", "sensor_type", "name", "unit", "job", "group", "tool"
    )
    assert "name condition tool temp" == test_sensor.name
    assert (
        "name condition tool temp-http://192.168.1.35/path/api" == test_sensor.unique_id
    )
    assert not test_sensor.device_class


def test_is_on():
    """Test the is_on property."""
    api = mock.MagicMock()
    api.api_url = "http://192.168.1.35/path/api"
    test_sensor = sensor.OctoPrintSensor(
        api, "condition", "sensor_type", "name", "unit", "job", "group"
    )
    api.update.return_value = 36
    test_sensor.update()
    assert 36 == test_sensor.state

    api.update.return_value = 45
    test_sensor.update()
    assert 45 == test_sensor.state
