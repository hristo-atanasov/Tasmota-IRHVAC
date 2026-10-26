"""Run inside the HA container: python -m unittest discover -s tests -p test_hvac_presets.py.

All MQTT transport is mocked; these tests never operate an appliance.
"""

from copy import deepcopy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import homeassistant  # noqa: F401  # Initialize HA's schema compatibility first.
from homeassistant.core import State
from homeassistant.helpers.restore_state import RestoreEntity

from custom_components.tasmota_irhvac import climate
from custom_components.tasmota_irhvac.presets import PRESET_FROST

CONFIGS = {
    "gree": {
        "name": "Gree heat pump",
        "vendor": "GREE",
        "hvac_model": "YAW1F",
        "command_topic": "cmnd/gree_ac/irhvac",
        "state_topic": "tele/gree_ac/RESULT",
        "min_temp": 16,
        "max_temp": 30,
        "target_temp": 20,
        "supported_modes": ["heat", "cool", "fan_only", "off"],
        "supported_fan_speeds": ["medium", "high", "auto"],
        "frost_protection": {
            "command": "econo",
            "temperature": 8,
            "comfort_temperature": 20,
        },
    },
    "fujitsu": {
        "name": "Fujitsu heat pump",
        "vendor": "FUJITSU_AC",
        "hvac_model": "ARRAH2E",
        "command_topic": "cmnd/fujitsu_ac/irhvac",
        "state_topic": "tele/fujitsu_ac/RESULT",
        "min_temp": 16,
        "max_temp": 30,
        "target_temp": 20,
        "supported_modes": ["heat", "cool", "fan_only", "off"],
        "supported_fan_speeds": ["medium", "high", "auto"],
        "frost_protection": {
            "command": "irsend",
            "temperature": 10,
            "comfort_temperature": 20,
            "topic": "cmnd/fujitsu_ac/irsend",
            "payload": {
                "Protocol": "FUJITSU_AC",
                "Bits": 128,
                "Data": "0x1463001010FE0930410B001806122034",
            },
            "match_state": {"Power": "On", "Mode": "Fan", "Temp": 10},
        },
    },
    "legacy": {
        "name": "Legacy heat pump",
        "vendor": "FUJITSU_AC",
        "command_topic": "cmnd/legacy_ac/irhvac",
        "state_topic": "tele/legacy_ac/RESULT",
        "away_temp": 10,
        "target_temp": 20,
        "min_temp": 10,
    },
}


class PresetTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.transport = patch.object(
            climate.mqtt, "async_publish", new_callable=AsyncMock
        )
        self.publish = self.transport.start()
        self.addCleanup(self.transport.stop)

    def entity(self, filename="gree", **overrides):
        values = deepcopy(CONFIGS[filename])
        values["platform"] = "tasmota_irhvac"
        values.update(overrides)
        config = climate.PLATFORM_SCHEMA(values)
        hass = SimpleNamespace(
            config=SimpleNamespace(units=SimpleNamespace(temperature_unit="°C")),
            states=SimpleNamespace(get=lambda _: None),
        )
        e = climate.TasmotaIrhvac(hass, config["vendor"], config)
        e.async_schedule_update_ha_state = lambda: None
        e.async_write_ha_state = lambda: None
        return e

    def payload(self):
        return json.loads(self.publish.call_args.args[2])

    async def receiver(self, e):
        subscriptions = {}

        async def subscribe(hass, topic, handler):
            subscriptions[topic] = handler
            return lambda: None

        with patch.object(climate.mqtt, "async_subscribe", side_effect=subscribe):
            await e._subscribe_topics()

        async def receive(data):
            await subscriptions[e.state_topic](
                SimpleNamespace(payload=json.dumps(data))
            )

        return receive

    async def test_native_frost_commands(self):
        for device, target in (("gree", 8), ("fujitsu", 10)):
            with self.subTest(device=device):
                e = self.entity(device)
                await e.async_set_preset_mode(PRESET_FROST)
                self.assertEqual(
                    (e.hvac_mode, e.preset_mode, e.target_temperature),
                    ("heat", PRESET_FROST, target),
                )
                if device == "gree":
                    self.assertEqual(self.payload()["Econo"], "on")
                    self.assertEqual(self.payload()["Temp"], 20)
                else:
                    self.assertEqual(
                        self.publish.call_args.args[1], "cmnd/fujitsu_ac/irsend"
                    )
                    self.assertEqual(
                        self.payload(), CONFIGS[device]["frost_protection"]["payload"]
                    )

    async def test_leaving_frost_uses_normal_irhvac_commands(self):
        actions = {
            "comfort": (
                "async_set_preset_mode",
                {"preset_mode": "comfort"},
                "heat",
                20,
            ),
            "none": ("async_set_preset_mode", {"preset_mode": "none"}, "heat", 23),
            "temperature": ("async_set_temperature", {"temperature": 22}, "heat", 22),
            "cool": ("async_set_hvac_mode", {"hvac_mode": "cool"}, "cool", 23),
            "off": ("async_turn_off", {}, "off", 23),
        }
        for device in ("gree", "fujitsu"):
            for action, (method, kwargs, mode, target) in actions.items():
                with self.subTest(device=device, action=action):
                    e = self.entity(device)
                    await e.async_set_temperature(temperature=23, hvac_mode="heat")
                    await e.async_set_fan_mode("auto")
                    await e.async_set_preset_mode(PRESET_FROST)
                    await getattr(e, method)(**kwargs)
                    self.assertEqual(
                        (e.hvac_mode, e.target_temperature), (mode, target)
                    )
                    self.assertEqual(
                        e.preset_mode, "comfort" if action == "comfort" else "none"
                    )
                    self.assertEqual(e.fan_mode, "auto")
                    self.assertEqual(self.publish.call_args.args[1], e.topic)
                    self.assertEqual(self.payload()["Temp"], target)
                    self.assertEqual(
                        self.payload()["Power"], "off" if action == "off" else "on"
                    )
                    self.assertEqual(self.payload()["Econo"], "off")

    async def test_native_feedback_preserves_the_normal_target(self):
        raw = CONFIGS["fujitsu"]["frost_protection"]["payload"]
        cases = [
            ("gree", {"Power": "On", "Mode": "Heat", "Temp": 16, "Econo": "On"}, {}),
            ("fujitsu", {"Power": "On", "Mode": "Fan", "Temp": 10}, {}),
            ("fujitsu", {"Power": "On", "Mode": "Fan", "Temp": 10}, raw),
            ("fujitsu", None, raw),
        ]
        for device, state, frame in cases:
            with self.subTest(device=device, raw=bool(frame)):
                e = self.entity(device)
                await e.async_set_temperature(temperature=23, hvac_mode="heat")
                if state is None:
                    await e.async_turn_off()
                receive = await self.receiver(e)
                self.publish.reset_mock()
                message = dict(frame)
                if state is not None:
                    message["IRHVAC"] = {"Vendor": CONFIGS[device]["vendor"], **state}
                await receive({"IrReceived": message})
                self.assertEqual((e.hvac_mode, e.preset_mode), ("heat", PRESET_FROST))
                self.assertEqual(e.target_temperature, 8 if device == "gree" else 10)
                self.publish.assert_not_awaited()
                await e.async_set_preset_mode("none")
                self.assertEqual(e.target_temperature, 23)

    async def test_remote_commands_clear_frost(self):
        for device in ("gree", "fujitsu"):
            for mode in ("heat", "off"):
                with self.subTest(device=device, mode=mode):
                    e = self.entity(device)
                    receive = await self.receiver(e)
                    await e.async_set_preset_mode(PRESET_FROST)
                    await receive(
                        {
                            "IRHVAC": {
                                "Vendor": CONFIGS[device]["vendor"],
                                "Power": "Off" if mode == "off" else "On",
                                "Mode": "Heat",
                                "Temp": 23,
                                "Econo": "Off",
                            }
                        }
                    )
                    self.assertEqual((e.hvac_mode, e.preset_mode), (mode, "none"))
                    if mode == "heat":
                        self.assertEqual(e.target_temperature, 23)

    async def test_partial_feedback_keeps_frost(self):
        for device, fields in (
            ("gree", {"FanSpeed": "Auto"}),
            ("fujitsu", {"Mode": "Fan"}),
        ):
            with self.subTest(device=device):
                e = self.entity(device)
                receive = await self.receiver(e)
                await e.async_set_preset_mode(PRESET_FROST)
                await receive(
                    {"IRHVAC": {"Vendor": CONFIGS[device]["vendor"], **fields}}
                )
                self.assertEqual((e.hvac_mode, e.preset_mode), ("heat", PRESET_FROST))
                await e.async_set_preset_mode("none")
                self.assertEqual(self.payload()["Mode"], "heat")

    async def test_restart_restores_frost_without_transmitting(self):
        for device, target in (("gree", 8), ("fujitsu", 10)):
            with self.subTest(device=device):
                e = self.entity(device)
                e.async_get_last_state = AsyncMock(
                    return_value=State(
                        "climate.test",
                        "heat",
                        {
                            "temperature": target,
                            "preset_mode": PRESET_FROST,
                            "normal_target_temperature": 23,
                            "normal_fan_mode": "medium",
                            "last_on_mode": "heat",
                        },
                    )
                )
                self.publish.reset_mock()
                with (
                    patch.object(
                        RestoreEntity, "async_added_to_hass", new_callable=AsyncMock
                    ),
                    patch.object(
                        climate.mqtt,
                        "async_wait_for_mqtt_client",
                        new_callable=AsyncMock,
                    ),
                    patch.object(
                        climate.mqtt, "async_subscribe", new_callable=AsyncMock
                    ),
                    patch.object(climate.ha_event, "async_track_state_change_event"),
                ):
                    await e.async_added_to_hass()
                self.assertEqual(
                    (e.preset_mode, e.target_temperature), (PRESET_FROST, target)
                )
                self.publish.assert_not_awaited()
                await e.async_set_preset_mode("none")
                self.assertEqual((e.target_temperature, e.fan_mode), (23, "medium"))

    async def test_raw_feedback_requires_configured_protocol_and_match(self):
        config = deepcopy(CONFIGS["fujitsu"]["frost_protection"])
        config.pop("match_state")
        e = self.entity("fujitsu", frost_protection=config)
        receive = await self.receiver(e)
        await receive(
            {
                "IRHVAC": {
                    "Vendor": "FUJITSU_AC",
                    "Power": "On",
                    "Mode": "Fan",
                    "Temp": 10,
                }
            }
        )
        self.assertNotEqual(e.preset_mode, PRESET_FROST)
        await receive({"IrReceived": {**config["payload"], "Protocol": "GREE"}})
        self.assertNotEqual(e.preset_mode, PRESET_FROST)

    async def test_power_off_overrides_raw_frost_feedback(self):
        e = self.entity("fujitsu")
        receive = await self.receiver(e)
        await receive(
            {
                "IrReceived": {
                    **CONFIGS["fujitsu"]["frost_protection"]["payload"],
                    "IRHVAC": {
                        "Vendor": "FUJITSU_AC",
                        "Power": "Off",
                        "Mode": "Fan",
                        "Temp": 10,
                    },
                }
            }
        )
        self.assertEqual((e.hvac_mode, e.preset_mode), ("off", "none"))

    async def test_econo_service_enters_and_leaves_frost(self):
        e = self.entity()
        await e.async_set_econo("on", "SendStore")
        self.assertEqual(e.preset_mode, PRESET_FROST)
        await e.async_set_econo("off", "SendStore")
        self.assertEqual(e.preset_mode, "none")
        self.assertEqual(self.payload()["Econo"], "off")

    async def test_raw_frost_respects_store_only(self):
        e = self.entity("fujitsu")
        await e.async_set_preset_mode(PRESET_FROST)
        self.publish.reset_mock()
        await e.async_set_turbo("on", "StoreOnly")
        self.publish.assert_not_awaited()

    async def test_opt_out_keeps_existing_away_behavior(self):
        e = self.entity("legacy")
        self.assertEqual(e.preset_modes, ["none", "away"])
        await e.async_set_temperature(temperature=22, hvac_mode="heat")
        await e.async_set_preset_mode("away")
        self.assertEqual(e.target_temperature, 10)
        await e.async_set_preset_mode("none")
        self.assertEqual(e.target_temperature, 22)


if __name__ == "__main__":
    unittest.main()
