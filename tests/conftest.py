"""Shared fixtures and helpers for Tasmota IRHVAC tests."""

import json

import pytest
from homeassistant.components.climate.const import (
    FAN_AUTO,
    HVACMode,
    SWING_OFF,
    SWING_VERTICAL,
)
from homeassistant.const import CONF_NAME, PRECISION_WHOLE
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tasmota_irhvac.const import (
    CONF_AVAILABILITY_TOPIC,
    CONF_AWAY_TEMP,
    CONF_BEEP,
    CONF_CELSIUS,
    CONF_CLEAN,
    CONF_COMMAND_TOPIC,
    CONF_ECONO,
    CONF_FAN_LIST,
    CONF_FILTER,
    CONF_IGNORE_OFF_TEMP,
    CONF_INITIAL_OPERATION_MODE,
    CONF_KEEP_MODE,
    CONF_LIGHT,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_MODEL,
    CONF_MODES_LIST,
    CONF_MQTT_DELAY,
    CONF_POWER_SENSOR,
    CONF_PRECISION,
    CONF_QUIET,
    CONF_SLEEP,
    CONF_SPECIAL_MODE,
    CONF_STATE_TOPIC,
    CONF_STATE_TOPIC_2,
    CONF_SWING_LIST,
    CONF_TARGET_TEMP,
    CONF_TEMP_SENSOR,
    CONF_TEMP_STEP,
    CONF_TOGGLE_LIST,
    CONF_TURBO,
    CONF_VENDOR,
    DATA_KEY,
    DOMAIN,
    HVAC_FAN_AUTO_MAX,
    HVAC_FAN_MAX_HIGH,
    HVAC_FAN_MEDIUM,
    HVAC_FAN_MIN,
)

# ---------------------------------------------------------------------------
# Default config builder
# ---------------------------------------------------------------------------

# Keys stored in entry.data (connection/identity)
_DATA_DEFAULTS = {
    CONF_NAME: "Test AC",
    CONF_VENDOR: "SAMSUNG_AC",
    CONF_COMMAND_TOPIC: "cmnd/tasmota_ac/irhvac",
    CONF_STATE_TOPIC: "tele/tasmota_ac/RESULT",
}

# Keys stored in entry.options (everything else)
_OPTIONS_DEFAULTS = {
    CONF_MQTT_DELAY: 0,
    CONF_MIN_TEMP: 16,
    CONF_MAX_TEMP: 32,
    CONF_TARGET_TEMP: 26,
    CONF_PRECISION: PRECISION_WHOLE,
    CONF_TEMP_STEP: PRECISION_WHOLE,
    CONF_CELSIUS: "on",
    CONF_IGNORE_OFF_TEMP: False,
    CONF_MODES_LIST: [
        HVACMode.OFF,
        HVACMode.HEAT,
        HVACMode.COOL,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
        HVACMode.AUTO,
    ],
    CONF_FAN_LIST: [HVAC_FAN_AUTO_MAX, HVAC_FAN_MAX_HIGH, HVAC_FAN_MEDIUM, HVAC_FAN_MIN],
    CONF_SWING_LIST: [SWING_OFF, SWING_VERTICAL],
    CONF_INITIAL_OPERATION_MODE: HVACMode.OFF,
    CONF_KEEP_MODE: False,
    CONF_QUIET: "off",
    CONF_TURBO: "off",
    CONF_ECONO: "off",
    CONF_MODEL: "-1",
    CONF_LIGHT: "off",
    CONF_FILTER: "off",
    CONF_CLEAN: "off",
    CONF_BEEP: "off",
    CONF_SLEEP: "-1",
    CONF_TOGGLE_LIST: [],
    CONF_SPECIAL_MODE: "",
}


def make_config(overrides=None):
    """Build a full {data, options} dict pair with sensible defaults.

    Returns (data_dict, options_dict).  Pass overrides to replace any key
    in either dict.
    """
    data = dict(_DATA_DEFAULTS)
    options = dict(_OPTIONS_DEFAULTS)
    if overrides:
        for key, val in overrides.items():
            if key in _DATA_DEFAULTS:
                data[key] = val
            else:
                options[key] = val
    return data, options


def make_mqtt_state_payload(overrides=None):
    """Build a JSON MQTT state payload (the IRHVAC sub-object Tasmota sends).

    The outer envelope mirrors ``tele/.../RESULT`` format.
    """
    irhvac = {
        "Vendor": "SAMSUNG_AC",
        "Model": "-1",
        "Mode": "cool",
        "Power": "on",
        "Celsius": "on",
        "Temp": 24,
        "FanSpeed": "auto",
        "SwingV": "off",
        "SwingH": "off",
        "Quiet": "off",
        "Turbo": "off",
        "Econo": "off",
        "Light": "off",
        "Filter": "off",
        "Clean": "off",
        "Beep": "off",
        "Sleep": "-1",
    }
    if overrides:
        irhvac.update(overrides)
    return json.dumps({"IRHVAC": irhvac})


def make_config_entry(data=None, options=None):
    """Create a MockConfigEntry ready for hass."""
    if data is None or options is None:
        d, o = make_config()
        data = data or d
        options = options or o
    return MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=1,
        data=data,
        options=options,
        title=data.get(CONF_NAME, "Test AC"),
        unique_id=f"{data[CONF_VENDOR]}_{data[CONF_COMMAND_TOPIC]}",
    )


async def setup_integration(hass: HomeAssistant, entry=None):
    """Set up the integration with a MockConfigEntry and return the entry."""
    if entry is None:
        entry = make_config_entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def get_climate_entity(hass: HomeAssistant, entry):
    """Return the climate entity stored for the given config entry."""
    return hass.data[DATA_KEY].get(entry.entry_id)
