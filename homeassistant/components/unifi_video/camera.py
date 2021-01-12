"""Support for Ubiquiti's UVC cameras."""
import logging
import re

from uvcclient import camera as uvc_camera, nvr

from homeassistant.components.camera import SUPPORT_STREAM, Camera
from homeassistant.helpers import entity_platform
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SERVICE_REBOOT

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Discover cameras on a Unifi NVR."""

    nvrconn = hass.data[DOMAIN]["nvrconn"]
    coordinator = hass.data[DOMAIN]["coordinator"]
    identifier = hass.data[DOMAIN]["camera_id_field"]

    async_add_devices(
        [
            UnifiVideoCamera(
                coordinator,
                nvrconn,
                coordinator.data[camera][identifier],
                coordinator.data[camera]["name"],
                hass.data[DOMAIN]["camera_password"],
            )
            for camera in coordinator.data
        ],
        True,
    )

    platform = entity_platform.current_platform.get()

    platform.async_register_entity_service(
        SERVICE_REBOOT,
        {},
        "async_reboot",
    )

    return True


class UnifiVideoCamera(CoordinatorEntity, Camera):
    """A Ubiquiti Unifi Video Camera."""

    def __init__(self, coordinator, camera, uuid, name, password):
        """Initialize an Unifi camera."""
        super().__init__(coordinator)
        Camera.__init__(self)
        self._nvr = camera
        self._uuid = uuid
        self._name = name
        self._password = password
        self.is_streaming = False
        self._connect_addr = None
        self._camera = None
        self._motion_status = False

    @property
    def device_info(self):
        """Device info."""
        return {
            "identifiers": {(DOMAIN, self._uuid)},
            "manufacturer": "Ubiquiti",
            "model": self._caminfo["model"],
        }

    @property
    def _caminfo(self):
        return self.coordinator.data[self._uuid]

    @property
    def name(self):
        """Return the name of this camera."""
        return self._name

    @property
    def supported_features(self):
        """Return supported features."""
        channels = self._caminfo["channels"]
        for channel in channels:
            if channel["isRtspEnabled"]:
                return SUPPORT_STREAM

        return 0

    @property
    def is_recording(self):
        """Return true if the camera is recording."""
        return self._caminfo["recordingSettings"]["fullTimeRecordEnabled"]

    @property
    def motion_detection_enabled(self):
        """Camera Motion Detection Status."""
        return self._caminfo["recordingSettings"]["motionRecordEnabled"]

    @property
    def unique_id(self) -> str:
        """Return a unique identifier for this client."""
        return self._uuid

    @property
    def brand(self):
        """Return the brand of this camera."""
        return "Ubiquiti"

    @property
    def model(self):
        """Return the model of this camera."""
        return self._caminfo["model"]

    def _login(self):
        """Login to the camera."""
        caminfo = self._caminfo
        if self._connect_addr:
            addrs = [self._connect_addr]
        else:
            addrs = [caminfo["host"], caminfo["internalHost"]]

        if self._nvr.server_version >= (3, 2, 0):
            client_cls = uvc_camera.UVCCameraClientV320
        else:
            client_cls = uvc_camera.UVCCameraClient

        if caminfo["username"] is None:
            caminfo["username"] = "ubnt"

        camera = None
        for addr in addrs:
            try:
                camera = client_cls(addr, caminfo["username"], self._password)
                camera.login()
                _LOGGER.debug(
                    "Logged into UVC camera %(name)s via %(addr)s",
                    {"name": self._name, "addr": addr},
                )
                self._connect_addr = addr
                break
            except OSError:
                pass
            except uvc_camera.CameraConnectError:
                pass
            except uvc_camera.CameraAuthError:
                pass
        if not self._connect_addr:
            _LOGGER.error("Unable to login to camera")
            return None

        self._camera = camera
        return True

    def camera_image(self):
        """Return the image of this camera."""

        if not self._camera:
            if not self._login():
                return

        def _get_image(retry=True):
            try:
                return self._camera.get_snapshot()
            except uvc_camera.CameraConnectError:
                _LOGGER.error("Unable to contact camera")
            except uvc_camera.CameraAuthError:
                if retry:
                    self._login()
                    return _get_image(retry=False)
                _LOGGER.error("Unable to log into camera, unable to get snapshot")
                raise

        return _get_image()

    def set_motion_detection(self, mode):
        """Set motion detection on or off."""
        set_mode = "motion" if mode is True else "none"

        try:
            self._nvr.set_recordmode(self._uuid, set_mode)
            self._motion_status = mode
        except nvr.NvrError as err:
            _LOGGER.error("Unable to set recordmode to %s", set_mode)
            _LOGGER.debug(err)

    def enable_motion_detection(self):
        """Enable motion detection in camera."""
        self.set_motion_detection(True)

    def disable_motion_detection(self):
        """Disable motion detection in camera."""
        self.set_motion_detection(False)

    async def async_reboot(self):
        """Reboots the camera."""
        await self.hass.async_add_executor_job(self.reboot)

    def reboot(self):
        """Reboots the camera."""
        if not self._camera:
            if not self._login():
                return

        def _reboot(retry=True):
            try:
                return self._camera.reboot()
            except uvc_camera.CameraConnectError:
                _LOGGER.error("Unable to contact camera")
            except uvc_camera.CameraAuthError:
                if retry:
                    self._login()
                    return _reboot(retry=False)
                _LOGGER.error("Unable to log into camera, unable to reboot")
                raise

        return _reboot()

    async def stream_source(self):
        """Return the source of the stream."""
        for channel in self._caminfo["channels"]:
            if channel["isRtspEnabled"]:
                uri = next(
                    (
                        uri
                        for i, uri in enumerate(channel["rtspUris"])
                        # pylint: disable=protected-access
                        if re.search(self._nvr._host, uri)
                        # pylint: enable=protected-access
                    )
                )
                return uri

        return None
