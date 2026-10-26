"""Opt-in native frost protection and comfort presets."""

import asyncio
import json
import math

import voluptuous as vol

from homeassistant.components import mqtt
from homeassistant.components.climate.const import (
    ClimateEntityFeature,
    HVACMode,
    PRESET_COMFORT,
    PRESET_NONE,
)
from homeassistant.exceptions import ServiceValidationError

PRESET_FROST = "Frost protection"


def valid_temperature(value):
    """Reject missing, non-finite and non-numeric temperatures."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def finite_temperature(value):
    """Validate a temperature expressed in the device's native units."""
    if isinstance(value, bool):
        raise vol.Invalid("Temperature must be a finite number")
    try:
        value = float(value)
    except (TypeError, ValueError) as error:
        raise vol.Invalid("Temperature must be a finite number") from error
    if not math.isfinite(value):
        raise vol.Invalid("Temperature must be a finite number")
    return value


def validate_frost_command(config):
    """Require a complete raw command and reject irrelevant raw-only options."""
    if config["command"] == "irsend":
        if "topic" not in config or "payload" not in config:
            raise vol.Invalid("irsend frost protection requires topic and payload")
        payload = config["payload"]
        if len(payload["Data"][2:]) * 4 != payload["Bits"]:
            raise vol.Invalid("Payload Data length must match Bits")
    elif any(key in config for key in ("topic", "payload", "match_state")):
        raise vol.Invalid("topic, payload and match_state require command: irsend")
    return config


FROST_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Required("command"): vol.In(["econo", "irsend"]),
            vol.Required("temperature"): finite_temperature,
            vol.Optional("comfort_temperature", default=20): finite_temperature,
            vol.Optional("topic"): mqtt.valid_publish_topic,
            vol.Optional("payload"): vol.Schema(
                {
                    vol.Required("Protocol"): str,
                    vol.Required("Bits"): vol.All(int, vol.Range(min=1)),
                    vol.Required("Data"): vol.Match(r"^0x[0-9a-fA-F]+$"),
                }
            ),
            vol.Optional("match_state"): vol.Schema(
                {
                    str: vol.Any(str, int, float, bool),
                }
            ),
        }
    ),
    validate_frost_command,
)


def _matches_state(payload, expected):
    """Compare only explicitly configured decoded fields, ignoring string case."""
    return bool(expected) and all(
        key in payload and str(payload[key]).lower() == str(value).lower()
        for key, value in expected.items()
    )


class ClimatePresets:
    """Translate common presets into the configured device's native commands."""

    def __init__(self, entity, config):
        self.entity = entity
        self.command = config["command"]
        self.frost_temperature = config["temperature"]
        self.comfort_temperature = config["comfort_temperature"]
        self.topic = config.get("topic")
        self.payload = config.get("payload")
        self.match_state = config.get("match_state", {})
        if self.command == "econo" and entity._vendor != "GREE":
            raise ValueError("The econo frost command is only configured for GREE")
        if self.payload and self.payload["Protocol"] != entity._vendor:
            raise ValueError("Frost payload protocol must match the climate vendor")
        if not self._normal_temperature(self.comfort_temperature):
            raise ValueError("comfort_temperature must be inside min_temp/max_temp")
        if HVACMode.HEAT not in entity._attr_hvac_modes:
            raise ValueError("Frost protection requires heat in supported_modes")
        self.normal_target = self.comfort_temperature
        self.normal_fan = entity._attr_fan_mode
        entity._attr_preset_modes = [PRESET_NONE, PRESET_FROST, PRESET_COMFORT]
        entity._attr_preset_mode = PRESET_NONE
        entity._support_flags |= ClimateEntityFeature.PRESET_MODE
        # Gree's frost bit describes a persistent state, not a one-shot command.
        if self.command == "econo":
            entity._toggle_list = [v for v in entity._toggle_list if v != "Econo"]
            entity._econo = "off"

    def _normal_temperature(self, value):
        e = self.entity
        return valid_temperature(value) and e._min_temp <= value <= e._max_temp

    @property
    def active(self):
        return self.entity._attr_preset_mode == PRESET_FROST

    @property
    def attributes(self):
        return {
            "normal_target_temperature": self.normal_target,
            "normal_fan_mode": self.normal_fan,
        }

    @property
    def command_temperature(self):
        # Native Gree frost protection uses Econo with a normal encoded setpoint.
        return (
            self.normal_target if self.active else self.entity._attr_target_temperature
        )

    def _remember_normal(self):
        e = self.entity
        if not self.active:
            if self._normal_temperature(e._attr_target_temperature):
                self.normal_target = e._attr_target_temperature
            self.normal_fan = e._attr_fan_mode

    def activate(self, *, remember=True):
        e = self.entity
        if remember:
            self._remember_normal()
        e._is_away = False
        e._attr_preset_mode = PRESET_FROST
        e._attr_hvac_mode = e._last_on_mode = HVACMode.HEAT
        e.power_mode = "on"
        e._enabled = True
        e._attr_target_temperature = self.frost_temperature
        e._attr_fan_mode = "auto"
        e._turbo = "off"
        e._sleep = "-1"
        if self.command == "econo":
            e._econo = "on"

    def leave(self):
        e = self.entity
        if self.active:
            e._attr_target_temperature = self.normal_target
            e._attr_fan_mode = self.normal_fan
            e._clean = "off"
        e._attr_preset_mode = PRESET_NONE
        e._is_away = False
        if self.command == "econo":
            e._econo = "off"

    def prepare_temperature(self, temperature, hvac_mode):
        was_active = self.active
        self.leave()
        self.normal_target = temperature
        if was_active and hvac_mode is None:
            e = self.entity
            e._attr_hvac_mode = e._last_on_mode = HVACMode.HEAT
            e.power_mode = "on"
            e._enabled = True

    async def set_preset(self, preset):
        e = self.entity
        if preset == PRESET_FROST:
            self.activate()
        elif preset in (PRESET_COMFORT, PRESET_NONE):
            self.leave()
            if preset == PRESET_COMFORT:
                self.normal_target = self.comfort_temperature
                e._attr_target_temperature = self.comfort_temperature
                e._attr_hvac_mode = e._last_on_mode = HVACMode.HEAT
                e.power_mode = "on"
                e._enabled = True
                e._attr_preset_mode = PRESET_COMFORT
        else:
            raise ServiceValidationError(f"Unsupported preset: {preset}")
        await e.send_ir()

    async def send_raw_if_active(self):
        if not self.active:
            return False
        e = self.entity
        # Other control changes must never send an ordinary heat frame while frosted.
        self.activate()
        if self.command != "irsend":
            return False
        if e._state_mode == "StoreOnly":
            e._state_mode = "SendStore"
            e.async_schedule_update_ha_state()
            return True
        if e._mqtt_delay:
            await asyncio.sleep(e._mqtt_delay)
        await mqtt.async_publish(e.hass, self.topic, json.dumps(self.payload))
        e._state_mode = "SendStore"
        e.async_schedule_update_ha_state()
        return True

    def restore(self, old_state):
        """Restore intent without transmitting IR or turning an AC on."""
        e = self.entity
        attrs = old_state.attributes if old_state else {}
        normal = attrs.get("normal_target_temperature")
        if self._normal_temperature(normal):
            self.normal_target = normal
        elif self._normal_temperature(e._attr_target_temperature):
            self.normal_target = e._attr_target_temperature
        fan = attrs.get("normal_fan_mode")
        if fan in (e._attr_fan_modes or []):
            self.normal_fan = fan
        if (
            old_state
            and old_state.state == HVACMode.HEAT
            and attrs.get("preset_mode") == PRESET_FROST
        ):
            self.activate(remember=False)
        else:
            e._attr_target_temperature = self.normal_target
            e._attr_preset_mode = (
                PRESET_COMFORT
                if attrs.get("preset_mode") == PRESET_COMFORT
                and e._attr_hvac_mode == HVACMode.HEAT
                and self.normal_target == self.comfort_temperature
                else PRESET_NONE
            )
            e._is_away = False
            if self.command == "econo":
                e._econo = "off"

    def feedback(self, message, payload):
        """Recognize native frost frames and reconcile ordinary remote changes."""
        e = self.entity
        if payload and payload.get("Vendor") != e._vendor:
            return
        power = str(payload.get("Power", e.power_mode)).lower()
        mode = str(payload.get("Mode", e._attr_hvac_mode)).lower()
        temperature = payload.get("Temp")
        raw_frost = False
        if self.payload and message.get("Protocol") == self.payload["Protocol"]:
            data = str(message.get("Data", "")).lower().removeprefix("0x")
            raw_frost = data == self.payload["Data"].lower().removeprefix("0x")
        if power == "off" and ("Power" in payload or not raw_frost):
            self.leave()
            e._attr_hvac_mode = HVACMode.OFF
            e.power_mode = "off"
            e._enabled = False
            return
        if raw_frost:
            self.activate(remember=False)
            return
        if not payload:
            return
        is_frost = (
            self.command == "econo"
            and mode == "heat"
            and str(payload.get("Econo", "")).lower() == "on"
        ) or (self.command == "irsend" and _matches_state(payload, self.match_state))
        if is_frost:
            self.activate(remember=False)
            return
        # Partial telemetry (e.g. just fan speed) does not cancel an active preset.
        changed_mode = "Mode" in payload and mode != "heat"
        if (
            self.command == "irsend"
            and mode == str(self.match_state.get("Mode")).lower()
        ):
            # Some native frost functions are encoded as fan mode. Wait for
            # a setpoint or another explicit mode before treating that as normal fan.
            changed_mode = False
        ordinary_command = (
            changed_mode
            or self.command == "econo"
            and str(payload.get("Econo", "")).lower() == "off"
            or self.command == "irsend"
            and self._normal_temperature(temperature)
        )
        if self.active:
            if not ordinary_command:
                e._attr_hvac_mode = e._last_on_mode = HVACMode.HEAT
                e._attr_target_temperature = self.frost_temperature
                return
            self.leave()
            # The ordinary remote's setpoint takes precedence over the saved one.
            if self._normal_temperature(temperature):
                e._attr_target_temperature = temperature
        if self._normal_temperature(e._attr_target_temperature):
            self.normal_target = e._attr_target_temperature
        else:
            e._attr_target_temperature = self.normal_target
        if e._attr_preset_mode == PRESET_COMFORT and (
            mode != "heat" or e._attr_target_temperature != self.comfort_temperature
        ):
            e._attr_preset_mode = PRESET_NONE
