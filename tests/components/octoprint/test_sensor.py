"""The tests for Octoptint binary sensor module."""
import asyncio
import logging
import unittest
from unittest import mock

from homeassistant.components.octoprint import sensor
from homeassistant.components.octoprint.const import DOMAIN

from tests.common import get_test_home_assistant

_LOGGER = logging.getLogger(__name__)


class TestOctoprintSensorSetup(unittest.TestCase):
    """Test the Octoptint sensor platform."""

    def setUp(self):
        """Set up things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.addCleanup(self.hass.stop)
        self.api = mock.MagicMock()

    def test_setup_config(self):
        """Test component setup."""
        self.hass.data[DOMAIN] = {"foo": self.api}

        add_entities = mock.MagicMock()
        config_entry = mock.MagicMock()
        config_entry.entry_id = "foo"
        config_entry.data = {
            "host": "http://192.168.1.35/",
            "name": "name",
            "sensors": ["Printing"],
        }
        assert asyncio.run_coroutine_threadsafe(
            sensor.async_setup_entry(self.hass, config_entry, add_entities),
            self.hass.loop,
        ).result()
        self.hass.block_till_done()

        assert add_entities.call_count == 1


class TestOctoprintSensor(unittest.TestCase):
    """Test class for Octoptint binary sensor."""

    def setup_method(self, method):
        """Set up the mock API."""
        self.uuid = "06e3ff29-8048-31c2-8574-0852d1bd0e03"
        self.name = "name"
        self.hass = get_test_home_assistant()
        self.api = mock.MagicMock()
        self.api.api_url = "http://192.168.1.35/path/api"
        self.addCleanup(self.hass.stop)
        self.sensor = sensor.OctoPrintSensor(
            self.api, "condition", "sensor_type", "name", "unit", "job", "group"
        )

    def test_properties(self):
        """Test the properties."""
        assert "name condition" == self.sensor.name
        assert "name condition-http://192.168.1.35/path/api" == self.sensor.unique_id
        assert not self.sensor.device_class

    def test_properties_with_tool(self):
        """Test the properties."""
        self.sensor = sensor.OctoPrintSensor(
            self.api, "condition", "sensor_type", "name", "unit", "job", "group", "tool"
        )
        assert "name condition tool temp" == self.sensor.name
        assert (
            "name condition tool temp-http://192.168.1.35/path/api"
            == self.sensor.unique_id
        )
        assert not self.sensor.device_class

    def test_device_info(self):
        """Test device information."""
        assert {
            ("octoprint", "http://192.168.1.35/path/api")
        } == self.sensor.device_info["identifiers"]

    def test_is_on(self):
        """Test the is_on property."""
        self.api.update.return_value = 36
        self.sensor.update()
        assert 36 == self.sensor.state

        self.api.update.return_value = 45
        self.sensor.update()
        assert 45 == self.sensor.state
