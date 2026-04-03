"""Tests for MQTT state handling in the Tasmota IRHVAC climate entity."""

import json

import pytest
from homeassistant.components.climate.const import HVACMode
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import async_fire_mqtt_message

from custom_components.tasmota_irhvac.const import DATA_KEY

from tests.conftest import (
    get_climate_entity,
    make_mqtt_state_payload,
    setup_integration,
)


async def test_mqtt_state_updates_mode(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """MQTT payload updates the HVAC mode."""
    entry = await setup_integration(hass)
    entity = get_climate_entity(hass, entry)
    assert entity is not None

    # Entity starts in OFF mode
    assert entity.hvac_mode == HVACMode.OFF

    # Fire an MQTT message that sets the mode to "cool" with power "on"
    payload = make_mqtt_state_payload({"Mode": "cool", "Power": "on", "Vendor": "SAMSUNG_AC"})
    async_fire_mqtt_message(hass, "tele/tasmota_ac/RESULT", payload)
    await hass.async_block_till_done()

    assert entity.hvac_mode == HVACMode.COOL


async def test_mqtt_state_updates_temperature(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """MQTT payload updates the target temperature."""
    entry = await setup_integration(hass)
    entity = get_climate_entity(hass, entry)

    payload = make_mqtt_state_payload({"Temp": 22, "Power": "on", "Mode": "heat", "Vendor": "SAMSUNG_AC"})
    async_fire_mqtt_message(hass, "tele/tasmota_ac/RESULT", payload)
    await hass.async_block_till_done()

    assert entity.target_temperature == 22


async def test_mqtt_state_updates_fan(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """MQTT payload updates the fan mode."""
    entry = await setup_integration(hass)
    entity = get_climate_entity(hass, entry)

    payload = make_mqtt_state_payload({"FanSpeed": "min", "Power": "on", "Mode": "cool", "Vendor": "SAMSUNG_AC"})
    async_fire_mqtt_message(hass, "tele/tasmota_ac/RESULT", payload)
    await hass.async_block_till_done()

    assert entity.fan_mode == "min"


async def test_mqtt_ignores_wrong_vendor(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """MQTT payload from a different vendor is ignored."""
    entry = await setup_integration(hass)
    entity = get_climate_entity(hass, entry)

    original_temp = entity.target_temperature

    payload = make_mqtt_state_payload({"Vendor": "DAIKIN", "Temp": 18, "Power": "on", "Mode": "cool"})
    async_fire_mqtt_message(hass, "tele/tasmota_ac/RESULT", payload)
    await hass.async_block_till_done()

    # Temperature should not have changed
    assert entity.target_temperature == original_temp


async def test_mqtt_nested_ir_received(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """MQTT payload wrapped in IrReceived envelope is correctly parsed."""
    entry = await setup_integration(hass)
    entity = get_climate_entity(hass, entry)

    irhvac = {
        "Vendor": "SAMSUNG_AC",
        "Model": "-1",
        "Mode": "heat",
        "Power": "on",
        "Celsius": "on",
        "Temp": 28,
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
    payload = json.dumps({"IrReceived": {"Protocol": "SAMSUNG_AC", "IRHVAC": irhvac}})
    async_fire_mqtt_message(hass, "tele/tasmota_ac/RESULT", payload)
    await hass.async_block_till_done()

    assert entity.hvac_mode == HVACMode.HEAT
    assert entity.target_temperature == 28


async def test_send_ir_publishes_mqtt(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """Calling send_ir publishes a JSON payload to the command topic."""
    entry = await setup_integration(hass)
    entity = get_climate_entity(hass, entry)

    # Set mode so send_ir has something to send
    entity._attr_hvac_mode = HVACMode.COOL
    entity.power_mode = "on"
    entity._last_on_mode = HVACMode.COOL
    entity._attr_target_temperature = 24

    await entity.send_ir()
    await hass.async_block_till_done()

    # Check that mqtt.async_publish was called on the command topic
    assert mqtt_mock.async_publish.called
    call_args = mqtt_mock.async_publish.call_args
    topic = call_args[0][0]
    payload_str = call_args[0][1]

    assert topic == "cmnd/tasmota_ac/irhvac"
    payload_data = json.loads(payload_str)
    assert payload_data["Vendor"] == "SAMSUNG_AC"
    assert payload_data["Mode"] == HVACMode.COOL
    assert payload_data["Temp"] == 24
    assert payload_data["Power"] == "on"


async def test_availability_message(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """Availability topic updates entity availability."""
    entry = await setup_integration(hass)
    entity = get_climate_entity(hass, entry)

    # Default availability topic is derived: tele/<device>/LWT
    # For command topic "cmnd/tasmota_ac/irhvac", device is "tasmota_ac"
    avail_topic = "tele/tasmota_ac/LWT"

    # Online message
    async_fire_mqtt_message(hass, avail_topic, "Online")
    await hass.async_block_till_done()
    assert entity.available is True

    # Offline message
    async_fire_mqtt_message(hass, avail_topic, "Offline")
    await hass.async_block_till_done()
    assert entity.available is False

    # Back online
    async_fire_mqtt_message(hass, avail_topic, "Online")
    await hass.async_block_till_done()
    assert entity.available is True


async def test_mqtt_invalid_json_ignored(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """Invalid JSON on the state topic does not crash the entity."""
    entry = await setup_integration(hass)
    entity = get_climate_entity(hass, entry)

    original_mode = entity.hvac_mode

    async_fire_mqtt_message(hass, "tele/tasmota_ac/RESULT", "not valid json{{{")
    await hass.async_block_till_done()

    # Entity state unchanged
    assert entity.hvac_mode == original_mode


async def test_mqtt_payload_without_irhvac_ignored(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """MQTT JSON without an IRHVAC key is silently ignored."""
    entry = await setup_integration(hass)
    entity = get_climate_entity(hass, entry)

    original_temp = entity.target_temperature

    async_fire_mqtt_message(
        hass, "tele/tasmota_ac/RESULT", json.dumps({"StatusSNS": {"Time": "2024-01-01"}})
    )
    await hass.async_block_till_done()

    assert entity.target_temperature == original_temp
