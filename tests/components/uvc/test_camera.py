"""The tests for UVC camera module."""
import asyncio
from datetime import datetime
import logging
import socket
import unittest
from unittest import mock

import pytest
from uvcclient import camera

from homeassistant.components.camera import SUPPORT_STREAM
from homeassistant.components.uvc import camera as uvc
from homeassistant.components.uvc.const import DOMAIN
from homeassistant.helpers import entity_platform
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.setup import setup_component

from tests.common import get_test_home_assistant

_LOGGER = logging.getLogger(__name__)


class TestUVCSetup(unittest.TestCase):
    """Test the UVC camera platform."""

    def setUp(self):
        """Set up things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.addCleanup(self.hass.stop)
        self.coordinator = DataUpdateCoordinator(
            self.hass, _LOGGER, name="unifi-video-test"
        )

    @mock.patch("uvcclient.nvr.UVCRemote")
    @mock.patch.object(uvc, "UnifiVideoCamera")
    def test_setup_full_config(self, mock_uvc, mock_remote):
        """Test the setup with full configuration."""
        config = {
            "platform": DOMAIN,
            "nvr": "foo",
            "password": "bar",
            "port": 123,
            "key": "secret",
        }

        with mock.patch.object(self.hass.config_entries.flow, "async_init") as init:
            assert setup_component(self.hass, "camera", {"camera": config})
            self.hass.block_till_done()
            assert init.call_count == 1

    @mock.patch("uvcclient.nvr.UVCRemote")
    @mock.patch.object(uvc, "UnifiVideoCamera")
    def test_setup_config(self, mock_uvc, mock_remote):
        """Test component init."""
        self.hass.data[DOMAIN] = {}
        self.hass.data[DOMAIN]["coordinator"] = self.coordinator
        self.hass.data[DOMAIN]["camera_id_field"] = "id"
        self.hass.data[DOMAIN]["nvrconn"] = mock_uvc
        self.hass.data[DOMAIN]["camera_password"] = "password"

        self.coordinator.data = {
            "uuid-1": {"id": "uuid-1", "name": "camera-1"},
            "uuid-2": {"id": "uuid-2", "name": "camera-2"},
        }

        add_entities = mock.MagicMock()
        with mock.patch.object(entity_platform, "current_platform"):
            assert asyncio.run_coroutine_threadsafe(
                uvc.async_setup_entry(self.hass, {}, add_entities), self.hass.loop
            ).result()
            self.hass.block_till_done()

        assert add_entities.call_count == 1


class TestUnifiVideoCamera(unittest.TestCase):
    """Test class for UVC."""

    def setup_method(self, method):
        """Set up the mock camera."""
        self.nvr = mock.MagicMock()
        self.uuid = "06e3ff29-8048-31c2-8574-0852d1bd0e03"
        self.name = "name"
        self.password = "seekret"
        self.hass = get_test_home_assistant()
        self.addCleanup(self.hass.stop)
        self.coordinator = DataUpdateCoordinator(
            self.hass, _LOGGER, name="unifi-video-test"
        )
        self.coordinator.data = {
            "06e3ff29-8048-31c2-8574-0852d1bd0e03": {
                "model": "UVC Fake",
                "uuid": "06e3ff29-8048-31c2-8574-0852d1bd0e03",
                "recordingSettings": {
                    "fullTimeRecordEnabled": True,
                    "motionRecordEnabled": False,
                },
                "host": "host-a",
                "internalHost": "host-b",
                "username": "admin",
                "lastRecordingStartTime": 1610070992367,
                "channels": [
                    {
                        "id": "0",
                        "width": 1920,
                        "height": 1080,
                        "fps": 25,
                        "bitrate": 6000000,
                        "isRtspEnabled": True,
                        "rtspUris": [
                            "rtsp://host-a:7447/uuid_rtspchannel_0",
                            "rtsp://foo:7447/uuid_rtspchannel_0",
                        ],
                    },
                    {
                        "id": "1",
                        "width": 1024,
                        "height": 576,
                        "fps": 15,
                        "bitrate": 1200000,
                        "isRtspEnabled": False,
                        "rtspUris": [
                            "rtsp://host-a:7447/uuid_rtspchannel_1",
                            "rtsp://foo:7447/uuid_rtspchannel_1",
                        ],
                    },
                ],
            }
        }
        self.uvc = uvc.UnifiVideoCamera(
            self.coordinator, self.nvr, self.uuid, self.name, self.password
        )
        self.nvr.server_version = (3, 2, 0)

    def test_properties(self):
        """Test the properties."""
        assert self.name == self.uvc.name
        assert self.uvc.is_recording
        assert "Ubiquiti" == self.uvc.brand
        assert "UVC Fake" == self.uvc.model
        assert SUPPORT_STREAM == self.uvc.supported_features
        assert "06e3ff29-8048-31c2-8574-0852d1bd0e03" == self.uvc.unique_id

    def test_motion_recording_mode_properties(self):
        """Test the properties."""
        self.coordinator.data["06e3ff29-8048-31c2-8574-0852d1bd0e03"][
            "recordingSettings"
        ]["fullTimeRecordEnabled"] = False
        self.coordinator.data["06e3ff29-8048-31c2-8574-0852d1bd0e03"][
            "recordingSettings"
        ]["motionRecordEnabled"] = True
        assert not self.uvc.is_recording
        assert (
            datetime(2021, 1, 8, 1, 56, 32, 367000)
            == self.uvc.device_state_attributes["last_recording_start_time"]
        )

        self.coordinator.data["06e3ff29-8048-31c2-8574-0852d1bd0e03"][
            "recordingIndicator"
        ] = "DISABLED"
        assert not self.uvc.is_recording

        self.coordinator.data["06e3ff29-8048-31c2-8574-0852d1bd0e03"][
            "recordingIndicator"
        ] = "MOTION_INPROGRESS"
        assert self.uvc.is_recording

        self.coordinator.data["06e3ff29-8048-31c2-8574-0852d1bd0e03"][
            "recordingIndicator"
        ] = "MOTION_FINISHED"
        assert self.uvc.is_recording

    def test_device_info(self):
        """Test device information."""
        assert {
            ("uvc", "06e3ff29-8048-31c2-8574-0852d1bd0e03")
        } == self.uvc.device_info["identifiers"]
        assert "Ubiquiti" == self.uvc.device_info["manufacturer"]
        assert "UVC Fake" == self.uvc.device_info["model"]

    def test_stream(self):
        """Test the RTSP stream URI."""
        stream_source = yield from self.uvc.stream_source()
        assert stream_source == "rtsp://foo:7447/uuid_rtspchannel_0"

    @mock.patch("uvcclient.store.get_info_store")
    @mock.patch("uvcclient.camera.UVCCameraClientV320")
    def test_login(self, mock_camera, mock_store):
        """Test the login."""
        self.uvc._login()
        assert mock_camera.call_count == 1
        assert mock_camera.call_args == mock.call("host-a", "admin", "seekret")
        assert mock_camera.return_value.login.call_count == 1
        assert mock_camera.return_value.login.call_args == mock.call()

    @mock.patch("uvcclient.store.get_info_store")
    @mock.patch("uvcclient.camera.UVCCameraClient")
    def test_login_v31x(self, mock_camera, mock_store):
        """Test login with v3.1.x server."""
        self.nvr.server_version = (3, 1, 3)
        self.uvc._login()
        assert mock_camera.call_count == 1
        assert mock_camera.call_args == mock.call("host-a", "admin", "seekret")
        assert mock_camera.return_value.login.call_count == 1
        assert mock_camera.return_value.login.call_args == mock.call()

    @mock.patch("uvcclient.store.get_info_store")
    @mock.patch("uvcclient.camera.UVCCameraClientV320")
    def test_login_tries_both_addrs_and_caches(self, mock_camera, mock_store):
        """Test the login tries."""
        responses = [0]

        def mock_login(*a):
            """Mock login."""
            try:
                responses.pop(0)
                raise OSError
            except IndexError:
                pass

        mock_store.return_value.get_camera_password.return_value = None
        mock_camera.return_value.login.side_effect = mock_login
        self.uvc._login()
        assert 2 == mock_camera.call_count
        assert "host-b" == self.uvc._connect_addr

        mock_camera.reset_mock()
        self.uvc._login()
        assert mock_camera.call_count == 1
        assert mock_camera.call_args == mock.call("host-b", "admin", "seekret")
        assert mock_camera.return_value.login.call_count == 1
        assert mock_camera.return_value.login.call_args == mock.call()

    @mock.patch("uvcclient.store.get_info_store")
    @mock.patch("uvcclient.camera.UVCCameraClientV320")
    def test_login_fails_both_properly(self, mock_camera, mock_store):
        """Test if login fails properly."""
        mock_camera.return_value.login.side_effect = socket.error
        assert self.uvc._login() is None
        assert self.uvc._connect_addr is None

    def test_camera_image_tries_login_bails_on_failure(self):
        """Test retrieving failure."""
        with mock.patch.object(self.uvc, "_login") as mock_login:
            mock_login.return_value = False
            assert self.uvc.camera_image() is None
            assert mock_login.call_count == 1
            assert mock_login.call_args == mock.call()

    def test_camera_image_logged_in(self):
        """Test the login state."""
        self.uvc._camera = mock.MagicMock()
        assert self.uvc._camera.get_snapshot.return_value == self.uvc.camera_image()

    def test_camera_image_error(self):
        """Test the camera image error."""
        self.uvc._camera = mock.MagicMock()
        self.uvc._camera.get_snapshot.side_effect = camera.CameraConnectError
        assert self.uvc.camera_image() is None

    def test_camera_image_reauths(self):
        """Test the re-authentication."""
        responses = [0]

        def mock_snapshot():
            """Mock snapshot."""
            try:
                responses.pop()
                raise camera.CameraAuthError()
            except IndexError:
                pass
            return "image"

        self.uvc._camera = mock.MagicMock()
        self.uvc._camera.get_snapshot.side_effect = mock_snapshot
        with mock.patch.object(self.uvc, "_login") as mock_login:
            assert "image" == self.uvc.camera_image()
            assert mock_login.call_count == 1
            assert mock_login.call_args == mock.call()
            assert [] == responses

    def test_camera_image_reauths_only_once(self):
        """Test if the re-authentication only happens once."""
        self.uvc._camera = mock.MagicMock()
        self.uvc._camera.get_snapshot.side_effect = camera.CameraAuthError
        with mock.patch.object(self.uvc, "_login") as mock_login:
            with pytest.raises(camera.CameraAuthError):
                self.uvc.camera_image()
            assert mock_login.call_count == 1
            assert mock_login.call_args == mock.call()

    def test_reboot(self):
        """Test rebooting the camera."""
        self.uvc._camera = mock.MagicMock()
        self.uvc.reboot()

        self.uvc._camera.reboot.assert_called_once()

    def test_reboot_with_login(self):
        """Test rebooting the camera."""
        self.uvc._camera = None
        with mock.patch.object(self.uvc, "_login") as mock_login:

            def side_effect(*args, **kwargs):
                self.uvc._camera = mock.MagicMock()

            mock_login.side_effect = side_effect

            self.uvc.reboot()
            assert mock_login.call_count == 1
            assert mock_login.call_args == mock.call()

    def test_reboot_attempts_reauths_only_once(self):
        """Test if the re-authentication only happens once."""
        self.uvc._camera = mock.MagicMock()
        self.uvc._camera.reboot.side_effect = camera.CameraAuthError
        with mock.patch.object(self.uvc, "_login") as mock_login:
            with pytest.raises(camera.CameraAuthError):
                self.uvc.reboot()
            assert mock_login.call_count == 1
            assert mock_login.call_args == mock.call()

    def test_reboot_error(self):
        """Test the camera image error."""
        self.uvc._camera = mock.MagicMock()
        self.uvc._camera.reboot.side_effect = camera.CameraConnectError
        assert self.uvc.reboot() is None
