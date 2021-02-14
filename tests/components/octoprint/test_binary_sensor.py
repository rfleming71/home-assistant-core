"""The tests for Octoptint binary sensor module."""
import logging
from unittest import mock

from homeassistant.components.octoprint import binary_sensor as sensor
from homeassistant.components.octoprint.const import DOMAIN
from homeassistant.const import STATE_OFF, STATE_ON

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
    test_sensor = sensor.OctoPrintBinarySensor(
        api, "condition", "sensor_type", "name", "unit", "job", "group", "tool"
    )
    assert "name condition" == test_sensor.name
    assert "name condition-http://192.168.1.35/path/api" == test_sensor.unique_id
    assert not test_sensor.device_class
    assert {("octoprint", "http://192.168.1.35/path/api")} == test_sensor.device_info[
        "identifiers"
    ]


def test_is_on():
    """Test the is_on property."""
    api = mock.MagicMock()
    api.api_url = "http://192.168.1.35/path/api"
    test_sensor = sensor.OctoPrintBinarySensor(
        api, "condition", "sensor_type", "name", "unit", "job", "group", "tool"
    )
    api.update.return_value = True
    test_sensor.update()
    assert STATE_ON == test_sensor.state

    api.update.return_value = False
    test_sensor.update()
    assert STATE_OFF == test_sensor.state
