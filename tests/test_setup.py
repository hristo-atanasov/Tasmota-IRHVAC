"""Tests for entry setup, unload, YAML import trigger, and service registration."""

import pytest
from homeassistant.components.climate.const import HVACMode
from homeassistant.core import HomeAssistant

from custom_components.tasmota_irhvac.const import (
    CONF_FAN_LIST,
    CONF_MODES_LIST,
    DATA_KEY,
    DOMAIN,
    HVAC_FAN_MAX,
)

from tests.conftest import get_climate_entity, make_config_entry, setup_integration


async def test_setup_entry_creates_entity(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """Setting up a config entry creates a climate entity in hass.data."""
    entry = await setup_integration(hass)
    entity = get_climate_entity(hass, entry)
    assert entity is not None
    assert entity.name == "Test AC"


async def test_unload_entry(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """Unloading an entry removes the entity from hass.data."""
    entry = await setup_integration(hass)
    assert get_climate_entity(hass, entry) is not None

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    # After unload, the entry should be cleaned from DOMAIN data
    assert entry.entry_id not in hass.data.get(DOMAIN, {})


async def test_yaml_import_triggers_config_flow(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """async_setup_platform triggers an import config flow that creates an entry."""
    from custom_components.tasmota_irhvac.climate import async_setup_platform

    config = {
        "name": "YAML Unit",
        "vendor": "DAIKIN",
        "command_topic": "cmnd/yaml_test/irhvac",
        "state_topic": "tele/yaml_test/RESULT",
        "mqtt_delay": 0,
        "min_temp": 16,
        "max_temp": 32,
        "target_temp": 26,
        "precision": 1,
        "temp_step": 1,
        "celsius_mode": "on",
        "default_quiet_mode": "off",
        "default_turbo_mode": "off",
        "default_econo_mode": "off",
        "hvac_model": "-1",
        "default_light_mode": "off",
        "default_filter_mode": "off",
        "default_clean_mode": "off",
        "default_beep_mode": "off",
        "default_sleep_mode": "-1",
        "keep_mode_when_off": False,
        "ignore_off_temp": False,
        "supported_modes": [HVACMode.OFF, HVACMode.COOL],
        "supported_fan_speeds": ["min"],
        "supported_swing_list": ["off"],
        "initial_operation_mode": HVACMode.OFF,
        "toggle_list": [],
        "special_mode": "",
    }

    # No entries before
    entries_before = hass.config_entries.async_entries(DOMAIN)
    assert len(entries_before) == 0

    await async_setup_platform(hass, config, lambda entities: None)
    await hass.async_block_till_done()

    # The import flow should have completed and created a config entry
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].data["vendor"] == "DAIKIN"


async def test_services_registered(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """After setup, IRHVAC services (set_econo, set_turbo, etc.) are registered."""
    await setup_integration(hass)

    expected_services = [
        "set_econo",
        "set_turbo",
        "set_quiet",
        "set_light",
        "set_filters",
        "set_clean",
        "set_beep",
        "set_sleep",
        "set_swingv",
        "set_swingh",
    ]
    for service_name in expected_services:
        assert hass.services.has_service(DOMAIN, service_name), (
            f"Service {DOMAIN}.{service_name} not registered"
        )


async def test_entity_state_after_setup(
    hass: HomeAssistant, enable_custom_integrations, mqtt_mock
):
    """Entity has correct initial state: modes, fan, target temp, etc."""
    entry = await setup_integration(hass)
    entity = get_climate_entity(hass, entry)
    assert entity is not None

    # Initial HVAC mode from config
    assert entity.hvac_mode == HVACMode.OFF

    # Fan modes should be set (default list has max_high/auto_max which map)
    assert entity.fan_modes is not None
    assert len(entity.fan_modes) > 0

    # Target temperature from config default
    assert entity.target_temperature == 26

    # Min/max temp
    assert entity.min_temp == 16
    assert entity.max_temp == 32

    # Supported modes from config
    assert HVACMode.OFF in entity.hvac_modes
    assert HVACMode.COOL in entity.hvac_modes
    assert HVACMode.HEAT in entity.hvac_modes
