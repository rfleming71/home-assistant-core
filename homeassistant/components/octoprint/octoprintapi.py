"""Simple JSON wrapper for OctoPrint's API."""
import logging
import time

from aiohttp.hdrs import CONTENT_TYPE
import requests

from homeassistant.const import CONTENT_TYPE_JSON

_LOGGER = logging.getLogger(__name__)


class OctoPrintAPI:
    """Simple JSON wrapper for OctoPrint's API."""

    def __init__(self, api_url, key, bed, number_of_tools):
        """Initialize OctoPrint API and set headers needed later."""
        self.api_url = api_url
        self.headers = {CONTENT_TYPE: CONTENT_TYPE_JSON, "X-Api-Key": key}
        self.printer_last_reading = [{}, None]
        self.job_last_reading = [{}, None]
        self._job_available = False
        self.printer_available = False
        self.printer_error_logged = False
        self.available = False
        self.available_error_logged = False
        self.job_error_logged = False
        self.bed = bed
        self.number_of_tools = number_of_tools

    def get_tools(self):
        """Get the list of tools that temperature is monitored on."""
        tools = []
        if self.number_of_tools > 0:
            for tool_number in range(0, self.number_of_tools):
                tools.append(f"tool{tool_number!s}")
        if self.bed:
            tools.append("bed")
        if not self.bed and self.number_of_tools == 0:
            temps = self.get("printer").get("temperature")
            if temps is not None:
                tools = temps.keys()
        return tools

    @property
    def job_available(self):
        """Is the printer job available."""
        return self._job_available

    def get(self, endpoint):
        """Send a get request, and return the response as a dict."""
        # Only query the API at most every 30 seconds
        now = time.time()
        if endpoint == "job":
            last_time = self.job_last_reading[1]
            if last_time is not None:
                if now - last_time < 30.0:
                    return self.job_last_reading[0]
        elif endpoint == "printer":
            last_time = self.printer_last_reading[1]
            if last_time is not None:
                if now - last_time < 30.0:
                    return self.printer_last_reading[0]

        url = self.api_url + endpoint
        try:
            response = requests.get(url, headers=self.headers, timeout=9)
            response.raise_for_status()
            if endpoint == "job":
                self.job_last_reading[0] = response.json()
                self.job_last_reading[1] = time.time()
                self._job_available = True
            elif endpoint == "printer":
                self.printer_last_reading[0] = response.json()
                self.printer_last_reading[1] = time.time()
                self.printer_available = True

            self.available = self.printer_available and self._job_available
            if self.available:
                self.job_error_logged = False
                self.printer_error_logged = False
                self.available_error_logged = False

            return response.json()

        except requests.ConnectionError as exc_con:
            log_string = "Failed to connect to Octoprint server. Error: %s" % exc_con

            if not self.available_error_logged:
                _LOGGER.error(log_string)
                self._job_available = False
                self.printer_available = False
                self.available_error_logged = True

            return None

        except requests.HTTPError as ex_http:
            status_code = ex_http.response.status_code

            log_string = "Failed to update OctoPrint status. Error: %s" % ex_http
            # Only log the first failure
            if endpoint == "job":
                log_string = f"Endpoint: job {log_string}"
                if not self.job_error_logged:
                    _LOGGER.error(log_string)
                    self.job_error_logged = True
                    self._job_available = False
            elif endpoint == "printer":
                if (
                    status_code == 409
                ):  # octoprint returns HTTP 409 when printer is not connected (and many other states)
                    self.printer_available = False
                else:
                    log_string = f"Endpoint: printer {log_string}"
                    if not self.printer_error_logged:
                        _LOGGER.error(log_string)
                        self.printer_error_logged = True
                        self.printer_available = False

            self.available = False

            return None

    def update(self, sensor_type, end_point, group, tool=None):
        """Return the value for sensor_type from the provided endpoint."""
        response = self.get(end_point)
        if response is not None:
            return get_value_from_json(response, sensor_type, group, tool)

        return response


def get_value_from_json(json_dict, sensor_type, group, tool):
    """Return the value for sensor_type from the JSON."""
    if group not in json_dict:
        return None

    if sensor_type in json_dict[group]:
        if sensor_type == "target" and json_dict[sensor_type] is None:
            return 0

        return json_dict[group][sensor_type]

    if tool is not None:
        if sensor_type in json_dict[group][tool]:
            return json_dict[group][tool][sensor_type]

    return None
