"""Tests for the Tasmota IRHVAC config flow (3-step wizard, import, reconfigure)."""

import pytest
from homeassistant.components.climate.const import HVACMode, SWING_OFF, SWING_VERTICAL
from homeassistant.const import CONF_NAME, PRECISION_HALVES, PRECISION_WHOLE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tasmota_irhvac.const import (
    CONF_AVAILABILITY_TOPIC,
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
    CONF_PRECISION,
    CONF_PROTOCOL,
    CONF_QUIET,
    CONF_SLEEP,
    CONF_SPECIAL_MODE,
    CONF_STATE_TOPIC,
    CONF_STATE_TOPIC_2,
    CONF_SWING_LIST,
    CONF_TARGET_TEMP,
    CONF_TEMP_STEP,
    CONF_TOGGLE_LIST,
    CONF_TURBO,
    CONF_VENDOR,
    DOMAIN,
    HVAC_FAN_AUTO_MAX,
    HVAC_FAN_MAX_HIGH,
    HVAC_FAN_MEDIUM,
    HVAC_FAN_MIN,
)


# ---------------------------------------------------------------------------
# Wizard step data
# ---------------------------------------------------------------------------

STEP1_INPUT = {
    CONF_NAME: "Living Room AC",
    CONF_VENDOR: "SAMSUNG_AC",
    CONF_COMMAND_TOPIC: "cmnd/ir_ac/irhvac",
    CONF_STATE_TOPIC: "tele/ir_ac/RESULT",
    CONF_MQTT_DELAY: 0,
}

STEP2_INPUT = {
    CONF_MIN_TEMP: 16,
    CONF_MAX_TEMP: 32,
    CONF_TARGET_TEMP: 24,
    CONF_PRECISION: str(PRECISION_WHOLE),
    CONF_TEMP_STEP: str(PRECISION_WHOLE),
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
}

STEP3_INPUT = {
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_user_step_shows_form(hass: HomeAssistant, enable_custom_integrations):
    """Step 1 of the wizard renders a form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_full_wizard_creates_entry(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """Completing all three wizard steps creates a config entry."""
    # Step 1
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], STEP1_INPUT
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "climate"

    # Step 2
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], STEP2_INPUT
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "advanced"

    # Step 3
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], STEP3_INPUT
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Living Room AC"

    # Connection keys live in data
    assert result["data"][CONF_VENDOR] == "SAMSUNG_AC"
    assert result["data"][CONF_COMMAND_TOPIC] == "cmnd/ir_ac/irhvac"
    assert result["data"][CONF_STATE_TOPIC] == "tele/ir_ac/RESULT"
    assert result["data"][CONF_NAME] == "Living Room AC"

    # Everything else lives in options
    assert result["options"][CONF_MIN_TEMP] == 16
    assert result["options"][CONF_MAX_TEMP] == 32
    assert result["options"][CONF_TARGET_TEMP] == 24
    assert result["options"][CONF_QUIET] == "off"


async def test_vendor_required(hass: HomeAssistant, enable_custom_integrations):
    """Step 1 rejects an empty vendor with an error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Test",
            CONF_VENDOR: "",
            CONF_COMMAND_TOPIC: "cmnd/test/irhvac",
            CONF_STATE_TOPIC: "tele/test/RESULT",
            CONF_MQTT_DELAY: 0,
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"][CONF_VENDOR] == "vendor_required"


async def test_duplicate_entry_aborted(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """A second entry with the same vendor+topic is aborted."""
    # Create first entry via the wizard
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], STEP1_INPUT
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], STEP2_INPUT
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], STEP3_INPUT
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY

    # Try again with identical step 1 data
    result2 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], STEP1_INPUT
    )
    result2 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], STEP2_INPUT
    )
    result2 = await hass.config_entries.flow.async_configure(
        result2["flow_id"], STEP3_INPUT
    )
    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_import_from_yaml(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """YAML import creates a config entry with correct data/options split."""
    yaml_config = {
        CONF_NAME: "Imported AC",
        CONF_VENDOR: "DAIKIN",
        CONF_COMMAND_TOPIC: "cmnd/daikin/irhvac",
        CONF_STATE_TOPIC: "tele/daikin/RESULT",
        CONF_MQTT_DELAY: 0.5,
        CONF_MIN_TEMP: 18,
        CONF_MAX_TEMP: 30,
        CONF_TARGET_TEMP: 22,
        CONF_PRECISION: PRECISION_WHOLE,
        CONF_TEMP_STEP: PRECISION_WHOLE,
        CONF_CELSIUS: "on",
        CONF_IGNORE_OFF_TEMP: False,
        CONF_MODES_LIST: [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT],
        CONF_FAN_LIST: [HVAC_FAN_AUTO_MAX, HVAC_FAN_MIN],
        CONF_SWING_LIST: [SWING_OFF],
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

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "import"}, data=yaml_config
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Imported AC"
    assert result["data"][CONF_VENDOR] == "DAIKIN"
    assert result["data"][CONF_COMMAND_TOPIC] == "cmnd/daikin/irhvac"
    # Options
    assert result["options"][CONF_MQTT_DELAY] == 0.5
    assert result["options"][CONF_MIN_TEMP] == 18


async def test_import_duplicate_aborted(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """YAML import with an existing entry (same vendor+topic) aborts."""
    yaml_config = {
        CONF_NAME: "AC",
        CONF_VENDOR: "LG",
        CONF_COMMAND_TOPIC: "cmnd/lg/irhvac",
        CONF_STATE_TOPIC: "tele/lg/RESULT",
        CONF_MQTT_DELAY: 0,
        CONF_MIN_TEMP: 16,
        CONF_MAX_TEMP: 32,
        CONF_TARGET_TEMP: 26,
        CONF_PRECISION: PRECISION_WHOLE,
        CONF_TEMP_STEP: PRECISION_WHOLE,
        CONF_CELSIUS: "on",
        CONF_QUIET: "off",
        CONF_TURBO: "off",
        CONF_ECONO: "off",
        CONF_MODEL: "-1",
        CONF_LIGHT: "off",
        CONF_FILTER: "off",
        CONF_CLEAN: "off",
        CONF_BEEP: "off",
        CONF_SLEEP: "-1",
        CONF_KEEP_MODE: False,
        CONF_IGNORE_OFF_TEMP: False,
        CONF_MODES_LIST: [HVACMode.OFF, HVACMode.COOL],
        CONF_FAN_LIST: [HVAC_FAN_MIN],
        CONF_SWING_LIST: [SWING_OFF],
        CONF_INITIAL_OPERATION_MODE: HVACMode.OFF,
        CONF_TOGGLE_LIST: [],
        CONF_SPECIAL_MODE: "",
    }

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "import"}, data=dict(yaml_config)
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY

    result2 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "import"}, data=dict(yaml_config)
    )
    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_import_normalizes_protocol_to_vendor(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """Old 'protocol' key is mapped to 'vendor' during import."""
    yaml_config = {
        CONF_NAME: "Old Config",
        CONF_PROTOCOL: "MITSUBISHI_AC",
        CONF_COMMAND_TOPIC: "cmnd/old/irhvac",
        CONF_STATE_TOPIC: "tele/old/RESULT",
        CONF_MQTT_DELAY: 0,
        CONF_MIN_TEMP: 16,
        CONF_MAX_TEMP: 32,
        CONF_TARGET_TEMP: 26,
        CONF_PRECISION: PRECISION_WHOLE,
        CONF_TEMP_STEP: PRECISION_WHOLE,
        CONF_CELSIUS: "on",
        CONF_QUIET: "off",
        CONF_TURBO: "off",
        CONF_ECONO: "off",
        CONF_MODEL: "-1",
        CONF_LIGHT: "off",
        CONF_FILTER: "off",
        CONF_CLEAN: "off",
        CONF_BEEP: "off",
        CONF_SLEEP: "-1",
        CONF_KEEP_MODE: False,
        CONF_IGNORE_OFF_TEMP: False,
        CONF_MODES_LIST: [HVACMode.OFF, HVACMode.COOL],
        CONF_FAN_LIST: [HVAC_FAN_MIN],
        CONF_SWING_LIST: [SWING_OFF],
        CONF_INITIAL_OPERATION_MODE: HVACMode.OFF,
        CONF_TOGGLE_LIST: [],
        CONF_SPECIAL_MODE: "",
    }

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "import"}, data=yaml_config
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_VENDOR] == "MITSUBISHI_AC"
    # protocol should NOT be in data (it was consumed)
    assert CONF_PROTOCOL not in result["data"]


async def test_import_handles_state_topic_2(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """Old 'state_topic_2' key format is preserved during import."""
    yaml_config = {
        CONF_NAME: "Dual Topic",
        CONF_VENDOR: "SAMSUNG_AC",
        CONF_COMMAND_TOPIC: "cmnd/dual/irhvac",
        CONF_STATE_TOPIC: "tele/dual/RESULT",
        # The old YAML key is "state_topic_2" (CONF_STATE_TOPIC + "_2")
        CONF_STATE_TOPIC + "_2": "tele/dual/RESULT2",
        CONF_MQTT_DELAY: 0,
        CONF_MIN_TEMP: 16,
        CONF_MAX_TEMP: 32,
        CONF_TARGET_TEMP: 26,
        CONF_PRECISION: PRECISION_WHOLE,
        CONF_TEMP_STEP: PRECISION_WHOLE,
        CONF_CELSIUS: "on",
        CONF_QUIET: "off",
        CONF_TURBO: "off",
        CONF_ECONO: "off",
        CONF_MODEL: "-1",
        CONF_LIGHT: "off",
        CONF_FILTER: "off",
        CONF_CLEAN: "off",
        CONF_BEEP: "off",
        CONF_SLEEP: "-1",
        CONF_KEEP_MODE: False,
        CONF_IGNORE_OFF_TEMP: False,
        CONF_MODES_LIST: [HVACMode.OFF, HVACMode.COOL],
        CONF_FAN_LIST: [HVAC_FAN_MIN],
        CONF_SWING_LIST: [SWING_OFF],
        CONF_INITIAL_OPERATION_MODE: HVACMode.OFF,
        CONF_TOGGLE_LIST: [],
        CONF_SPECIAL_MODE: "",
    }

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "import"}, data=yaml_config
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_STATE_TOPIC_2] == "tele/dual/RESULT2"


async def test_reconfigure_updates_entry(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """Reconfigure flow updates the config entry data."""
    from tests.conftest import make_config_entry, setup_integration

    entry = await setup_integration(hass)

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Renamed AC",
            CONF_VENDOR: "DAIKIN",
            CONF_COMMAND_TOPIC: "cmnd/new/irhvac",
            CONF_STATE_TOPIC: "tele/new/RESULT",
        },
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_NAME] == "Renamed AC"
    assert entry.data[CONF_VENDOR] == "DAIKIN"
    assert entry.data[CONF_COMMAND_TOPIC] == "cmnd/new/irhvac"


async def test_reconfigure_vendor_required(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """Reconfigure flow rejects empty vendor."""
    from tests.conftest import setup_integration

    entry = await setup_integration(hass)

    result = await entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Test",
            CONF_VENDOR: "",
            CONF_COMMAND_TOPIC: "cmnd/test/irhvac",
            CONF_STATE_TOPIC: "tele/test/RESULT",
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert result["errors"][CONF_VENDOR] == "vendor_required"


async def test_float_coercion(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """SelectSelector string values are coerced to float for precision/temp_step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], STEP1_INPUT
    )

    # Step 2: submit precision and temp_step as strings (as SelectSelector sends them)
    step2 = dict(STEP2_INPUT)
    step2[CONF_PRECISION] = str(PRECISION_HALVES)
    step2[CONF_TEMP_STEP] = str(PRECISION_HALVES)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], step2
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], STEP3_INPUT
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["options"][CONF_PRECISION] == PRECISION_HALVES
    assert isinstance(result["options"][CONF_PRECISION], float)
    assert result["options"][CONF_TEMP_STEP] == PRECISION_HALVES
    assert isinstance(result["options"][CONF_TEMP_STEP], float)
