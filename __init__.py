"""Provides functionality to interact with climate devices."""
from datetime import timedelta
import logging
import functools as ft

import voluptuous as vol

from homeassistant.helpers.temperature import display_temp as show_temp
from homeassistant.util.temperature import convert as convert_temperature
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.config_validation as config_validation

from .reproduce_state import async_reproduce_states  # noqa

_LOGGER = logging.getLogger(__name__)

from .const import (
    ATTR_TEMPERATURE,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    TEMP_CELSIUS,
    ATTR_AUX_HEAT,
    ATTR_AREA_ID,
    ATTR_AWAY_MODE,
    ATTR_CURRENT_HUMIDITY,
    ATTR_CURRENT_TEMPERATURE,
    ATTR_ENTITY_ID,
    ATTR_FAN_MODE,
    ATTR_FAN_MODES,
    ATTR_HUMIDITY,
    ATTR_HVAC_ACTIONS,
    ATTR_HVAC_MODE,
    ATTR_HVAC_MODES,
    ATTR_HOLD_MODE,
    ATTR_OPERATION_MODE,
    ATTR_MAX_HUMIDITY,
    ATTR_MAX_TEMP,
    ATTR_MIN_HUMIDITY,
    ATTR_MIN_TEMP,
    ATTR_PRESET_MODE,
    ATTR_PRESET_MODES,
    ATTR_SWING_MODE,
    ATTR_SWING_MODES,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ATTR_TARGET_TEMP_STEP,
    CONF_PLATFORM,
    CONF_ENTITY_NAMESPACE,
    CONF_SCAN_INTERVAL,
    DOMAIN,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_OFF,
    HVAC_MODES,
    SERVICE_SET_AUX_HEAT,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HUMIDITY,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_PRESET_MODE,
    SERVICE_SET_SWING_MODE,
    SERVICE_SET_TEMPERATURE,
    SERVICE_SET_AWAY_MODE,
    SERVICE_SET_HOLD_MODE,
    SERVICE_SET_OPERATION_MODE,
    SUPPORT_AUX_HEAT,
    SUPPORT_FAN_MODE,
    SUPPORT_PRESET_MODE,
    SUPPORT_SWING_MODE,
    SUPPORT_TARGET_HUMIDITY,
    SUPPORT_TARGET_TEMPERATURE_RANGE,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_TARGET_TEMPERATURE_HIGH,
    SUPPORT_TARGET_TEMPERATURE_LOW,
    SUPPORT_TARGET_HUMIDITY_LOW,
    SUPPORT_TARGET_HUMIDITY_HIGH,
    SUPPORT_OPERATION_MODE,
    ATTR_OPERATION_LIST,
    SUPPORT_HOLD_MODE,
    SUPPORT_AWAY_MODE,
    ATTR_FAN_LIST,
    ATTR_SWING_LIST,
    DEFAULT_MIN_HUMIDITY,
    DEFAULT_MAX_HUMIDITY,
)

# Schemas
PLATFORM_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PLATFORM): cv.string,
        vol.Optional(CONF_ENTITY_NAMESPACE): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL): cv.time_period,
    }
)

PLATFORM_SCHEMA_BASE = PLATFORM_SCHEMA.extend({}, extra=vol.ALLOW_EXTRA)

DEFAULT_MIN_TEMP = 7
DEFAULT_MAX_TEMP = 35
DEFAULT_MIN_HUMIDITY = 30
DEFAULT_MAX_HUMIDITY = 99

ENTITY_ID_FORMAT = DOMAIN + '.{}'
SCAN_INTERVAL = timedelta(seconds=60)

CONVERTIBLE_ATTRIBUTE = [
    ATTR_TEMPERATURE,
    ATTR_TARGET_TEMP_LOW,
    ATTR_TARGET_TEMP_HIGH,
]

async def async_setup_entry(hass, entry):
    """Set up a config entry."""
    return await hass.data[DOMAIN].async_setup_entry(entry)


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    return await hass.data[DOMAIN].async_unload_entry(entry)


class ClimateDevice(Entity):
    """Representation of a climate device."""

    @property
    def state(self):
        """Return the current state."""
        if self.is_on is False:
            return STATE_OFF
        if self.current_operation:
            return self.current_operation
        if self.is_on:
            return STATE_ON
        return None

    @property
    def precision(self):
        """Return the precision of the system."""
        if self.hass.config.units.temperature_unit == TEMP_CELSIUS:
            return PRECISION_TENTHS
        return PRECISION_WHOLE

    @property
    def state_attributes(self):
        """Return the optional state attributes."""
        data = {
            ATTR_CURRENT_TEMPERATURE: show_temp(
                self.hass, self.current_temperature, self.temperature_unit,
                self.precision),
            ATTR_MIN_TEMP: show_temp(
                self.hass, self.min_temp, self.temperature_unit,
                self.precision),
            ATTR_MAX_TEMP: show_temp(
                self.hass, self.max_temp, self.temperature_unit,
                self.precision),
            ATTR_TEMPERATURE: show_temp(
                self.hass, self.target_temperature, self.temperature_unit,
                self.precision),
        }

        supported_features = self.supported_features
        if self.target_temperature_step is not None:
            data[ATTR_TARGET_TEMP_STEP] = self.target_temperature_step

        if supported_features & SUPPORT_TARGET_TEMPERATURE_HIGH:
            data[ATTR_TARGET_TEMP_HIGH] = show_temp(
                self.hass, self.target_temperature_high, self.temperature_unit,
                self.precision)

        if supported_features & SUPPORT_TARGET_TEMPERATURE_LOW:
            data[ATTR_TARGET_TEMP_LOW] = show_temp(
                self.hass, self.target_temperature_low, self.temperature_unit,
                self.precision)

        if self.current_humidity is not None:
            data[ATTR_CURRENT_HUMIDITY] = self.current_humidity

        if supported_features & SUPPORT_TARGET_HUMIDITY:
            data[ATTR_HUMIDITY] = self.target_humidity

            if supported_features & SUPPORT_TARGET_HUMIDITY_LOW:
                data[ATTR_MIN_HUMIDITY] = self.min_humidity

            if supported_features & SUPPORT_TARGET_HUMIDITY_HIGH:
                data[ATTR_MAX_HUMIDITY] = self.max_humidity

        if supported_features & SUPPORT_FAN_MODE:
            data[ATTR_FAN_MODE] = self.current_fan_mode
            if self.fan_list:
                data[ATTR_FAN_LIST] = self.fan_list

        if supported_features & SUPPORT_OPERATION_MODE:
            data[ATTR_OPERATION_MODE] = self.current_operation
            if self.operation_list:
                data[ATTR_OPERATION_LIST] = self.operation_list

        if supported_features & SUPPORT_HOLD_MODE:
            data[ATTR_HOLD_MODE] = self.current_hold_mode

        if supported_features & SUPPORT_SWING_MODE:
            data[ATTR_SWING_MODE] = self.current_swing_mode
            if self.swing_list:
                data[ATTR_SWING_LIST] = self.swing_list

        if supported_features & SUPPORT_AWAY_MODE:
            is_away = self.is_away_mode_on
            data[ATTR_AWAY_MODE] = STATE_ON if is_away else STATE_OFF

        if supported_features & SUPPORT_AUX_HEAT:
            is_aux_heat = self.is_aux_heat_on
            data[ATTR_AUX_HEAT] = STATE_ON if is_aux_heat else STATE_OFF

        return data

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        raise NotImplementedError

    @property
    def current_humidity(self):
        """Return the current humidity."""
        return None

    @property
    def target_humidity(self):
        """Return the humidity we try to reach."""
        return None

    @property
    def current_operation(self):
        """Return current operation ie. heat, cool, idle."""
        return None

    @property
    def operation_list(self):
        """Return the list of available operation modes."""
        return None

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return None

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return None

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return None

    @property
    def target_temperature_high(self):
        """Return the highbound target temperature we try to reach."""
        return None

    @property
    def target_temperature_low(self):
        """Return the lowbound target temperature we try to reach."""
        return None

    @property
    def is_away_mode_on(self):
        """Return true if away mode is on."""
        return None

    @property
    def current_hold_mode(self):
        """Return the current hold mode, e.g., home, away, temp."""
        return None

    @property
    def is_on(self):
        """Return true if on."""
        return None

    @property
    def is_aux_heat_on(self):
        """Return true if aux heater."""
        return None

    @property
    def current_fan_mode(self):
        """Return the fan setting."""
        return None

    @property
    def fan_list(self):
        """Return the list of available fan modes."""
        return None

    @property
    def current_swing_mode(self):
        """Return the fan setting."""
        return None

    @property
    def swing_list(self):
        """Return the list of available swing modes."""
        return None

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        raise NotImplementedError()

    def async_set_temperature(self, **kwargs):
        """Set new target temperature.
        This method must be run in the event loop and returns a coroutine.
        """
        return self.hass.async_add_job(
            ft.partial(self.set_temperature, **kwargs))

    def set_humidity(self, humidity):
        """Set new target humidity."""
        raise NotImplementedError()

    def async_set_humidity(self, humidity):
        """Set new target humidity.
        This method must be run in the event loop and returns a coroutine.
        """
        return self.hass.async_add_job(self.set_humidity, humidity)

    def set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        raise NotImplementedError()

    def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode.
        This method must be run in the event loop and returns a coroutine.
        """
        return self.hass.async_add_job(self.set_fan_mode, fan_mode)

    def set_operation_mode(self, operation_mode):
        """Set new target operation mode."""
        raise NotImplementedError()

    def async_set_operation_mode(self, operation_mode):
        """Set new target operation mode.
        This method must be run in the event loop and returns a coroutine.
        """
        return self.hass.async_add_job(self.set_operation_mode, operation_mode)

    def set_swing_mode(self, swing_mode):
        """Set new target swing operation."""
        raise NotImplementedError()

    def async_set_swing_mode(self, swing_mode):
        """Set new target swing operation.
        This method must be run in the event loop and returns a coroutine.
        """
        return self.hass.async_add_job(self.set_swing_mode, swing_mode)

    def turn_away_mode_on(self):
        """Turn away mode on."""
        raise NotImplementedError()

    def async_turn_away_mode_on(self):
        """Turn away mode on.
        This method must be run in the event loop and returns a coroutine.
        """
        return self.hass.async_add_job(self.turn_away_mode_on)

    def turn_away_mode_off(self):
        """Turn away mode off."""
        raise NotImplementedError()

    def async_turn_away_mode_off(self):
        """Turn away mode off.
        This method must be run in the event loop and returns a coroutine.
        """
        return self.hass.async_add_job(self.turn_away_mode_off)

    def set_hold_mode(self, hold_mode):
        """Set new target hold mode."""
        raise NotImplementedError()

    def async_set_hold_mode(self, hold_mode):
        """Set new target hold mode.
        This method must be run in the event loop and returns a coroutine.
        """
        return self.hass.async_add_job(self.set_hold_mode, hold_mode)

    def turn_aux_heat_on(self):
        """Turn auxiliary heater on."""
        raise NotImplementedError()

    def async_turn_aux_heat_on(self):
        """Turn auxiliary heater on.
        This method must be run in the event loop and returns a coroutine.
        """
        return self.hass.async_add_job(self.turn_aux_heat_on)

    def turn_aux_heat_off(self):
        """Turn auxiliary heater off."""
        raise NotImplementedError()

    def async_turn_aux_heat_off(self):
        """Turn auxiliary heater off.
        This method must be run in the event loop and returns a coroutine.
        """
        return self.hass.async_add_job(self.turn_aux_heat_off)

    def turn_on(self):
        """Turn device on."""
        raise NotImplementedError()

    def async_turn_on(self):
        """Turn device on.
        This method must be run in the event loop and returns a coroutine.
        """
        return self.hass.async_add_job(self.turn_on)

    def turn_off(self):
        """Turn device off."""
        raise NotImplementedError()

    def async_turn_off(self):
        """Turn device off.
        This method must be run in the event loop and returns a coroutine.
        """
        return self.hass.async_add_job(self.turn_off)

    @property
    def supported_features(self):
        """Return the list of supported features."""
        raise NotImplementedError()

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return convert_temperature(DEFAULT_MIN_TEMP, TEMP_CELSIUS, self.temperature_unit)

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return convert_temperature(DEFAULT_MAX_TEMP, TEMP_CELSIUS, self.temperature_unit)

    @property
    def min_humidity(self):
        """Return the minimum humidity."""
        return DEFAULT_MIN_HUMITIDY

    @property
    def max_humidity(self):
        """Return the maximum humidity."""
        return DEFAULT_MAX_HUMIDITY


async def async_service_away_mode(entity, service):
    """Handle away mode service."""
    if service.data[ATTR_AWAY_MODE]:
        await entity.async_turn_away_mode_on()
    else:
        await entity.async_turn_away_mode_off()


async def async_service_aux_heat(entity, service):
    """Handle aux heat service."""
    if service.data[ATTR_AUX_HEAT]:
        await entity.async_turn_aux_heat_on()
    else:
        await entity.async_turn_aux_heat_off()


async def async_service_temperature_set(entity, service):
    """Handle set temperature service."""
    hass = entity.hass
    kwargs = {}

    for value, temp in service.data.items():
        if value in CONVERTIBLE_ATTRIBUTE:
            kwargs[value] = convert_temperature(
                temp,
                hass.config.units.temperature_unit,
                entity.temperature_unit
            )
        else:
            kwargs[value] = temp

    await entity.async_set_temperature(**kwargs)