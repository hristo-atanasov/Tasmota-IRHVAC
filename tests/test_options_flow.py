"""Tests for the Tasmota IRHVAC options flow (menu-driven)."""

import pytest
from homeassistant.components.climate.const import HVACMode, SWING_BOTH, SWING_OFF
from homeassistant.const import PRECISION_HALVES
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.tasmota_irhvac.const import (
    CONF_CELSIUS,
    CONF_FAN_LIST,
    CONF_IGNORE_OFF_TEMP,
    CONF_KEEP_MODE,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_MODES_LIST,
    CONF_MQTT_DELAY,
    CONF_PRECISION,
    CONF_QUIET,
    CONF_SPECIAL_MODE,
    CONF_SWING_LIST,
    CONF_TARGET_TEMP,
    CONF_TEMP_SENSOR,
    CONF_TEMP_STEP,
    CONF_TOGGLE_LIST,
    CONF_TURBO,
    HVAC_FAN_AUTO_MAX,
    HVAC_FAN_MIN,
)

from tests.conftest import setup_integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _start_options_flow(hass, entry):
    """Start the options flow and return the init result."""
    result = await hass.config_entries.options.async_init(entry.entry_id)
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_options_menu_shows(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """Init step shows the options menu."""
    entry = await setup_integration(hass)
    result = await _start_options_flow(hass, entry)
    assert result["type"] == FlowResultType.MENU
    assert result["step_id"] == "init"
    assert "mqtt" in result["menu_options"]
    assert "temperature" in result["menu_options"]
    assert "modes" in result["menu_options"]
    assert "defaults" in result["menu_options"]
    assert "sensors" in result["menu_options"]
    assert "advanced_options" in result["menu_options"]


async def test_mqtt_options(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """Changing MQTT delay via options flow updates the entry."""
    entry = await setup_integration(hass)
    result = await _start_options_flow(hass, entry)

    # Navigate to MQTT sub-step
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "mqtt"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "mqtt"

    # Submit new MQTT delay
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_MQTT_DELAY: 2.5}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_MQTT_DELAY] == 2.5


async def test_temperature_options(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """Changing temperature settings via options flow updates the entry."""
    entry = await setup_integration(hass)
    result = await _start_options_flow(hass, entry)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "temperature"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "temperature"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_MIN_TEMP: 18,
            CONF_MAX_TEMP: 28,
            CONF_TARGET_TEMP: 22,
            CONF_PRECISION: str(PRECISION_HALVES),
            CONF_TEMP_STEP: str(PRECISION_HALVES),
            CONF_CELSIUS: "on",
            CONF_IGNORE_OFF_TEMP: True,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_MIN_TEMP] == 18
    assert entry.options[CONF_MAX_TEMP] == 28
    assert entry.options[CONF_TARGET_TEMP] == 22
    # SelectSelector sends strings; coerced to float for storage
    assert entry.options[CONF_PRECISION] == PRECISION_HALVES
    assert isinstance(entry.options[CONF_PRECISION], float)
    assert entry.options[CONF_IGNORE_OFF_TEMP] is True


async def test_modes_options(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """Changing mode lists via options flow updates the entry."""
    entry = await setup_integration(hass)
    result = await _start_options_flow(hass, entry)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "modes"}
    )
    assert result["type"] == FlowResultType.FORM

    new_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT]
    new_fans = [HVAC_FAN_AUTO_MAX, HVAC_FAN_MIN]
    new_swings = [SWING_OFF, SWING_BOTH]

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_MODES_LIST: new_modes,
            CONF_FAN_LIST: new_fans,
            CONF_SWING_LIST: new_swings,
            CONF_KEEP_MODE: True,
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_MODES_LIST] == new_modes
    assert entry.options[CONF_FAN_LIST] == new_fans
    assert entry.options[CONF_SWING_LIST] == new_swings
    assert entry.options[CONF_KEEP_MODE] is True


async def test_defaults_options(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """Changing default quiet/turbo/etc via options flow updates the entry."""
    entry = await setup_integration(hass)
    result = await _start_options_flow(hass, entry)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "defaults"}
    )
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_QUIET: "on", CONF_TURBO: "on"},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_QUIET] == "on"
    assert entry.options[CONF_TURBO] == "on"


async def test_sensors_options(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """Setting and clearing temperature sensor via options flow."""
    entry = await setup_integration(hass)

    # Set a sensor
    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "sensors"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "sensors"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_TEMP_SENSOR: "sensor.room_temp"},
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_TEMP_SENSOR] == "sensor.room_temp"

    # Clear the sensor by not submitting it
    result = await _start_options_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "sensors"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    # When not submitted, the key should be absent from the merged options
    # (the options flow merges with existing, so the key persists from
    # the previous save unless the UI explicitly clears it -- this is an
    # OptionsFlowWithReload characteristic).


async def test_advanced_options(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """Changing toggle list and special mode via options flow."""
    entry = await setup_integration(hass)
    result = await _start_options_flow(hass, entry)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "advanced_options"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "advanced_options"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_TOGGLE_LIST: ["SwingV", "Quiet"],
            CONF_SPECIAL_MODE: "cool",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_TOGGLE_LIST] == ["SwingV", "Quiet"]
    assert entry.options[CONF_SPECIAL_MODE] == "cool"
