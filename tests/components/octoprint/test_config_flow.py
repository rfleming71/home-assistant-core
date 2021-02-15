"""Test the OctoPrint config flow."""
from unittest.mock import patch

from homeassistant import config_entries, data_entry_flow, setup
from homeassistant.components.octoprint.config_flow import CannotConnect, ConfigFlow
from homeassistant.components.octoprint.const import DOMAIN
from homeassistant.config_entries import SOURCE_IMPORT, SOURCE_ZEROCONF
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from tests.test_util.aiohttp import AiohttpClientMocker


async def test_form(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert not result["errors"]

    with patch(
        "homeassistant.components.octoprint.config_flow.validate_connection",
        return_value=True,
    ), patch(
        "homeassistant.components.octoprint.async_setup", return_value=True
    ) as mock_setup, patch(
        "homeassistant.components.octoprint.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "1.1.1.1",
                "api_key": "test-key",
                "name": "Printer",
                "port": 81,
                "ssl": True,
                "path": "/",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == "create_entry"
    assert result2["title"] == "Printer"
    assert result2["data"] == {
        "host": "1.1.1.1",
        "api_key": "test-key",
        "name": "Printer",
        "port": 81,
        "ssl": True,
        "path": "/",
    }
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_form_cannot_connect(hass):
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.octoprint.config_flow.validate_connection",
        side_effect=CannotConnect,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "http://1.1.1.1:80/path/",
                "api_key": "test-key",
                "name": "Printer",
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_unavailible(hass):
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.octoprint.config_flow.validate_connection",
        return_value=False,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "http://1.1.1.1:80/path/",
                "api_key": "test-key",
                "name": "Printer",
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_unknown_exception(hass):
    """Test we handle a random error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.octoprint.config_flow.validate_input",
        side_effect=Exception,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "host": "http://1.1.1.1:80/path/",
                "api_key": "test-key",
                "name": "Printer",
            },
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "unknown"}


async def test_show_zerconf_form(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test that the zeroconf confirmation form is served."""

    flow = ConfigFlow()
    flow.hass = hass
    flow.context = {"source": SOURCE_ZEROCONF}
    result = await flow.async_step_zeroconf(
        {
            "host": "192.168.1.123",
            "port": 80,
            "hostname": "example.local.",
            "properties": {"uuid": "83747482", "path": "/foo/"},
        }
    )

    assert flow.context["title_placeholders"] == {CONF_HOST: "192.168.1.123"}
    assert result["step_id"] == "user"
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM


async def test_import_yaml(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test that the zeroconf confirmation form is served."""

    flow = ConfigFlow()
    flow.hass = hass
    flow.context = {"source": SOURCE_IMPORT}
    with patch(
        "homeassistant.components.octoprint.config_flow.validate_connection",
        return_value=True,
    ):
        result = await flow.async_step_import(
            {
                "host": "192.168.1.123",
                "port": 80,
                "name": "Octoprint",
                "path": "/",
                "api_key": "123dfuchxxkks",
                "ssl": False,
            }
        )

    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY


async def test_duplicate_import_yaml(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Test that the zeroconf confirmation form is served."""

    flow = ConfigFlow()
    flow.hass = hass
    flow.context = {"source": SOURCE_IMPORT}
    current_config = [
        config_entries.ConfigEntry(
            1, DOMAIN, "config", {"host": "192.168.1.123"}, "IMPORT", "polling", {}
        )
    ]
    with patch(
        "homeassistant.config_entries.ConfigFlow._async_current_entries",
        return_value=current_config,
    ):
        result = await flow.async_step_import(
            {
                "host": "192.168.1.123",
                "port": 80,
                "name": "Octoprint",
                "path": "/",
                "api_key": "123dfuchxxkks",
                "ssl": False,
            }
        )

    assert result["type"] == data_entry_flow.RESULT_TYPE_ABORT
