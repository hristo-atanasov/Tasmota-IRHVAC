"""Adds support for generic thermostat units."""
import json
import logging
import uuid
import asyncio
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util

from homeassistant.components import mqtt

try:
    from homeassistant.components.mqtt.schemas import MQTT_AVAILABILITY_SCHEMA
except ImportError:
    from homeassistant.components.mqtt.mixins import MQTT_AVAILABILITY_SCHEMA

from homeassistant.components.climate import PLATFORM_SCHEMA as CLIMATE_PLATFORM_SCHEMA

# try:
#     from homeassistant.components.climate import ClimateEntity
# except ImportError:
#     from homeassistant.components.binary_sensor import ClimateDevice as ClimateEntity
from homeassistant.components.climate import ClimateEntity
from homeassistant.core import cached_property, callback

from homeassistant.helpers import event as ha_event
from homeassistant.helpers.restore_state import RestoreEntity

from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_DIFFUSE,
    FAN_FOCUS,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_MIDDLE,
    FAN_OFF,
    FAN_ON,
    HVACMode,
    HVACAction,
    ATTR_PRESET_MODE,
    ATTR_FAN_MODE,
    ATTR_SWING_MODE,
    ATTR_HVAC_MODE,
    PRESET_AWAY,
    PRESET_NONE,
    ClimateEntityFeature,
    SWING_BOTH,
    SWING_HORIZONTAL,
    SWING_OFF,
    SWING_VERTICAL,
)

from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    CONF_NAME,
    CONF_UNIQUE_ID,
    PRECISION_HALVES,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    STATE_ON,
    STATE_OFF,
    STATE_UNKNOWN,
    STATE_UNAVAILABLE,
    UnitOfTemperature,
)

from .const import (
    ATTR_ECONO,
    ATTR_TURBO,
    ATTR_QUIET,
    ATTR_LIGHT,
    ATTR_FILTERS,
    ATTR_CLEAN,
    ATTR_BEEP,
    ATTR_SLEEP,
    ATTR_SWINGV,
    ATTR_SWINGH,
    ATTR_LAST_ON_MODE,
    ATTR_STATE_MODE,
    ATTRIBUTES_IRHVAC,
    CONF_AVAILABILITY_TOPIC,
    STATE_AUTO,
    HVAC_FAN_AUTO,
    HVAC_FAN_MIN,
    HVAC_FAN_MEDIUM,
    HVAC_FAN_MAX,
    HVAC_MODE_AUTO_FAN,
    HVAC_MODE_FAN_AUTO,
    HVAC_FAN_MAX_HIGH,
    HVAC_FAN_AUTO_MAX,
    HVAC_MODES,
    CONF_EXCLUSIVE_GROUP_VENDOR,
    CONF_VENDOR,
    CONF_PROTOCOL,
    CONF_COMMAND_TOPIC,
    CONF_STATE_TOPIC,
    CONF_TEMP_SENSOR,
    CONF_HUMIDITY_SENSOR,
    CONF_POWER_SENSOR,
    CONF_MQTT_DELAY,
    CONF_MIN_TEMP,
    CONF_MAX_TEMP,
    CONF_TARGET_TEMP,
    CONF_INITIAL_OPERATION_MODE,
    CONF_AWAY_TEMP,
    CONF_PRECISION,
    CONF_TEMP_STEP,
    CONF_MODES_LIST,
    CONF_FAN_LIST,
    CONF_SWING_LIST,
    CONF_QUIET,
    CONF_TURBO,
    CONF_ECONO,
    CONF_MODEL,
    CONF_CELSIUS,
    CONF_LIGHT,
    CONF_FILTER,
    CONF_CLEAN,
    CONF_BEEP,
    CONF_SLEEP,
    CONF_KEEP_MODE,
    CONF_SWINGV,
    CONF_SWINGH,
    CONF_TOGGLE_LIST,
    CONF_IGNORE_OFF_TEMP,
    DATA_KEY,
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_STATE_TOPIC,
    DEFAULT_COMMAND_TOPIC,
    DEFAULT_MQTT_DELAY,
    DEFAULT_TARGET_TEMP,
    DEFAULT_MIN_TEMP,
    DEFAULT_MAX_TEMP,
    DEFAULT_PRECISION,
    DEFAULT_FAN_LIST,
    DEFAULT_CONF_QUIET,
    DEFAULT_CONF_TURBO,
    DEFAULT_CONF_ECONO,
    DEFAULT_CONF_MODEL,
    DEFAULT_CONF_CELSIUS,
    DEFAULT_CONF_LIGHT,
    DEFAULT_CONF_FILTER,
    DEFAULT_CONF_CLEAN,
    DEFAULT_CONF_BEEP,
    DEFAULT_CONF_SLEEP,
    DEFAULT_CONF_KEEP_MODE,
    DEFAULT_STATE_MODE,
    DEFAULT_IGNORE_OFF_TEMP,
    ON_OFF_LIST,
    STATE_MODE_LIST,
    SERVICE_ECONO_MODE,
    SERVICE_TURBO_MODE,
    SERVICE_QUIET_MODE,
    SERVICE_LIGHT_MODE,
    SERVICE_FILTERS_MODE,
    SERVICE_CLEAN_MODE,
    SERVICE_BEEP_MODE,
    SERVICE_SLEEP_MODE,
    SERVICE_SET_SWINGV,
    SERVICE_SET_SWINGH,
    TOGGLE_ALL_LIST,
)

DEFAULT_MODES_LIST = [
    HVACMode.COOL,
    HVACMode.HEAT,
    HVACMode.DRY,
    HVAC_MODE_AUTO_FAN,
    HVAC_MODE_FAN_AUTO,
]

DEFAULT_SWING_LIST = [SWING_OFF, SWING_VERTICAL]
DEFAULT_INITIAL_OPERATION_MODE = HVACMode.OFF

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE

if hasattr(ClimateEntityFeature, "TURN_ON"):
    SUPPORT_FLAGS |= ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF

PLATFORM_SCHEMA = CLIMATE_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
        vol.Exclusive(CONF_VENDOR, CONF_EXCLUSIVE_GROUP_VENDOR): cv.string,
        vol.Exclusive(CONF_PROTOCOL, CONF_EXCLUSIVE_GROUP_VENDOR): cv.string,
        vol.Required(
            CONF_COMMAND_TOPIC, default=DEFAULT_COMMAND_TOPIC
        ): mqtt.valid_publish_topic,
        vol.Optional(CONF_AVAILABILITY_TOPIC): mqtt.util.valid_topic,
        vol.Optional(CONF_TEMP_SENSOR): cv.entity_id,
        vol.Optional(CONF_HUMIDITY_SENSOR): cv.entity_id,
        vol.Optional(CONF_POWER_SENSOR): cv.entity_id,
        vol.Optional(
            CONF_STATE_TOPIC, default=DEFAULT_STATE_TOPIC
        ): mqtt.valid_subscribe_topic,
        vol.Optional(CONF_STATE_TOPIC + "_2"): mqtt.util.valid_topic,
        vol.Optional(CONF_MQTT_DELAY, default=DEFAULT_MQTT_DELAY): vol.Coerce(float),
        vol.Optional(CONF_MAX_TEMP, default=DEFAULT_MAX_TEMP): vol.Coerce(float),
        vol.Optional(CONF_MIN_TEMP, default=DEFAULT_MIN_TEMP): vol.Coerce(float),
        vol.Optional(CONF_TARGET_TEMP, default=DEFAULT_TARGET_TEMP): vol.Coerce(float),
        vol.Optional(
            CONF_INITIAL_OPERATION_MODE, default=DEFAULT_INITIAL_OPERATION_MODE
        ): vol.In(HVAC_MODES),
        vol.Optional(CONF_AWAY_TEMP): vol.Coerce(float),
        vol.Optional(CONF_PRECISION, default=DEFAULT_PRECISION): vol.In(
            [PRECISION_TENTHS, PRECISION_HALVES, PRECISION_WHOLE]
        ),
        vol.Optional(CONF_TEMP_STEP, default=PRECISION_WHOLE): vol.In(
            [PRECISION_HALVES, PRECISION_WHOLE]
        ),
        vol.Optional(CONF_MODES_LIST, default=DEFAULT_MODES_LIST): vol.All(
            cv.ensure_list, [vol.In(HVAC_MODES)]
        ),
        vol.Optional(CONF_FAN_LIST, default=DEFAULT_FAN_LIST): vol.All(
            cv.ensure_list,
            [
                vol.In(
                    [
                        FAN_ON,
                        FAN_OFF,
                        FAN_AUTO,
                        FAN_LOW,
                        FAN_MEDIUM,
                        FAN_HIGH,
                        FAN_MIDDLE,
                        FAN_FOCUS,
                        FAN_DIFFUSE,
                        HVAC_FAN_MIN,
                        HVAC_FAN_MEDIUM,
                        HVAC_FAN_MAX,
                        HVAC_FAN_AUTO,
                        HVAC_FAN_MAX_HIGH,
                        HVAC_FAN_AUTO_MAX,
                    ]
                )
            ],
        ),
        vol.Optional(CONF_SWING_LIST, default=DEFAULT_SWING_LIST): vol.All(
            cv.ensure_list,
            [vol.In([SWING_OFF, SWING_BOTH, SWING_VERTICAL, SWING_HORIZONTAL])],
        ),
        vol.Optional(CONF_QUIET, default=DEFAULT_CONF_QUIET): cv.string,
        vol.Optional(CONF_TURBO, default=DEFAULT_CONF_TURBO): cv.string,
        vol.Optional(CONF_ECONO, default=DEFAULT_CONF_ECONO): cv.string,
        vol.Optional(CONF_MODEL, default=DEFAULT_CONF_MODEL): cv.string,
        vol.Optional(CONF_CELSIUS, default=DEFAULT_CONF_CELSIUS): cv.string,
        vol.Optional(CONF_LIGHT, default=DEFAULT_CONF_LIGHT): cv.string,
        vol.Optional(CONF_FILTER, default=DEFAULT_CONF_FILTER): cv.string,
        vol.Optional(CONF_CLEAN, default=DEFAULT_CONF_CLEAN): cv.string,
        vol.Optional(CONF_BEEP, default=DEFAULT_CONF_BEEP): cv.string,
        vol.Optional(CONF_SLEEP, default=DEFAULT_CONF_SLEEP): cv.string,
        vol.Optional(CONF_KEEP_MODE, default=DEFAULT_CONF_KEEP_MODE): cv.boolean,
        vol.Optional(CONF_SWINGV): cv.string,
        vol.Optional(CONF_SWINGH): cv.string,
        vol.Optional(CONF_TOGGLE_LIST, default=[]): vol.All(
            cv.ensure_list,
            [vol.In(TOGGLE_ALL_LIST)],
        ),
        vol.Optional(CONF_IGNORE_OFF_TEMP, default=DEFAULT_IGNORE_OFF_TEMP): cv.boolean,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(MQTT_AVAILABILITY_SCHEMA.schema)
if hasattr(mqtt, "MQTT_BASE_PLATFORM_SCHEMA"):
    PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(mqtt.MQTT_BASE_PLATFORM_SCHEMA.schema)
else:
    PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(mqtt.config.MQTT_BASE_SCHEMA.schema)

IRHVAC_SERVICE_SCHEMA = vol.Schema({vol.Required(ATTR_ENTITY_ID): cv.entity_ids})

SERVICE_SCHEMA_ECONO_MODE = IRHVAC_SERVICE_SCHEMA.extend(
    {
        vol.Required(ATTR_ECONO): vol.In(ON_OFF_LIST),
        vol.Optional(ATTR_STATE_MODE, default=DEFAULT_STATE_MODE): vol.In(
            STATE_MODE_LIST
        ),
    }
)
SERVICE_SCHEMA_TURBO_MODE = IRHVAC_SERVICE_SCHEMA.extend(
    {
        vol.Required(ATTR_TURBO): vol.In(ON_OFF_LIST),
        vol.Optional(ATTR_STATE_MODE, default=DEFAULT_STATE_MODE): vol.In(
            STATE_MODE_LIST
        ),
    }
)
SERVICE_SCHEMA_QUIET_MODE = IRHVAC_SERVICE_SCHEMA.extend(
    {
        vol.Required(ATTR_QUIET): vol.In(ON_OFF_LIST),
        vol.Optional(ATTR_STATE_MODE, default=DEFAULT_STATE_MODE): vol.In(
            STATE_MODE_LIST
        ),
    }
)
SERVICE_SCHEMA_LIGHT_MODE = IRHVAC_SERVICE_SCHEMA.extend(
    {
        vol.Required(ATTR_LIGHT): vol.In(ON_OFF_LIST),
        vol.Optional(ATTR_STATE_MODE, default=DEFAULT_STATE_MODE): vol.In(
            STATE_MODE_LIST
        ),
    }
)
SERVICE_SCHEMA_FILTERS_MODE = IRHVAC_SERVICE_SCHEMA.extend(
    {
        vol.Required(ATTR_FILTERS): vol.In(ON_OFF_LIST),
        vol.Optional(ATTR_STATE_MODE, default=DEFAULT_STATE_MODE): vol.In(
            STATE_MODE_LIST
        ),
    }
)
SERVICE_SCHEMA_CLEAN_MODE = IRHVAC_SERVICE_SCHEMA.extend(
    {
        vol.Required(ATTR_CLEAN): vol.In(ON_OFF_LIST),
        vol.Optional(ATTR_STATE_MODE, default=DEFAULT_STATE_MODE): vol.In(
            STATE_MODE_LIST
        ),
    }
)
SERVICE_SCHEMA_BEEP_MODE = IRHVAC_SERVICE_SCHEMA.extend(
    {
        vol.Required(ATTR_BEEP): vol.In(ON_OFF_LIST),
        vol.Optional(ATTR_STATE_MODE, default=DEFAULT_STATE_MODE): vol.In(
            STATE_MODE_LIST
        ),
    }
)
SERVICE_SCHEMA_SLEEP_MODE = IRHVAC_SERVICE_SCHEMA.extend(
    {
        vol.Required(ATTR_SLEEP): cv.string,
        vol.Optional(ATTR_STATE_MODE, default=DEFAULT_STATE_MODE): vol.In(
            STATE_MODE_LIST
        ),
    }
)
SERVICE_SCHEMA_SET_SWINGV = IRHVAC_SERVICE_SCHEMA.extend(
    {
        vol.Required(ATTR_SWINGV): vol.In(
            ["off", "auto", "highest", "high", "middle", "low", "lowest"]
        ),
        vol.Optional(ATTR_STATE_MODE, default=DEFAULT_STATE_MODE): vol.In(
            STATE_MODE_LIST
        ),
    }
)
SERVICE_SCHEMA_SET_SWINGH = IRHVAC_SERVICE_SCHEMA.extend(
    {
        vol.Required(ATTR_SWINGH): vol.In(
            ["off", "auto", "left max", "left", "middle", "right", "right max", "wide"]
        ),
        vol.Optional(ATTR_STATE_MODE, default=DEFAULT_STATE_MODE): vol.In(
            STATE_MODE_LIST
        ),
    }
)

SERVICE_TO_METHOD = {
    SERVICE_ECONO_MODE: {
        "method": "async_set_econo",
        "schema": SERVICE_SCHEMA_ECONO_MODE,
    },
    SERVICE_TURBO_MODE: {
        "method": "async_set_turbo",
        "schema": SERVICE_SCHEMA_TURBO_MODE,
    },
    SERVICE_QUIET_MODE: {
        "method": "async_set_quiet",
        "schema": SERVICE_SCHEMA_QUIET_MODE,
    },
    SERVICE_LIGHT_MODE: {
        "method": "async_set_light",
        "schema": SERVICE_SCHEMA_LIGHT_MODE,
    },
    SERVICE_FILTERS_MODE: {
        "method": "async_set_filters",
        "schema": SERVICE_SCHEMA_FILTERS_MODE,
    },
    SERVICE_CLEAN_MODE: {
        "method": "async_set_clean",
        "schema": SERVICE_SCHEMA_CLEAN_MODE,
    },
    SERVICE_BEEP_MODE: {
        "method": "async_set_beep",
        "schema": SERVICE_SCHEMA_BEEP_MODE,
    },
    SERVICE_SLEEP_MODE: {
        "method": "async_set_sleep",
        "schema": SERVICE_SCHEMA_SLEEP_MODE,
    },
    SERVICE_SET_SWINGV: {
        "method": "async_set_swingv",
        "schema": SERVICE_SCHEMA_SET_SWINGV,
    },
    SERVICE_SET_SWINGH: {
        "method": "async_set_swingh",
        "schema": SERVICE_SCHEMA_SET_SWINGH,
    },
}


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the generic thermostat platform."""
    vendor = config.get(CONF_VENDOR)
    protocol = config.get(CONF_PROTOCOL)
    name = config.get(CONF_NAME)

    if DATA_KEY not in hass.data:
        hass.data[DATA_KEY] = {}

    if vendor is None:
        if protocol is None:
            _LOGGER.error('Neither vendor nor protocol provided for "%s"!', name)
            return

        vendor = protocol

    tasmotaIrhvac = TasmotaIrhvac(
        hass,
        vendor,
        config,
    )
    uuidstr = uuid.uuid4().hex
    hass.data[DATA_KEY][uuidstr] = tasmotaIrhvac

    async_add_entities([tasmotaIrhvac])

    async def async_service_handler(service):
        """Map services to methods on TasmotaIrhvac."""
        method = SERVICE_TO_METHOD.get(service.service, {})
        params = {
            key: value for key, value in service.data.items() if key != ATTR_ENTITY_ID
        }
        entity_ids = service.data.get(ATTR_ENTITY_ID)
        if entity_ids:
            devices = [
                device
                for device in hass.data[DATA_KEY].values()
                if device.entity_id in entity_ids
            ]
        else:
            devices = hass.data[DATA_KEY].values()

        update_tasks = []
        for device in devices:
            if not hasattr(device, method["method"]):
                continue
            await getattr(device, method["method"])(**params)
            update_tasks.append(asyncio.create_task(device.async_update_ha_state(True)))

        if update_tasks:
            await asyncio.wait(update_tasks)

    for irhvac_service in SERVICE_TO_METHOD:
        schema = SERVICE_TO_METHOD[irhvac_service].get("schema", IRHVAC_SERVICE_SCHEMA)
        hass.services.async_register(
            DOMAIN, irhvac_service, async_service_handler, schema=schema
        )


class TasmotaIrhvac(RestoreEntity, ClimateEntity):
    """Representation of a Generic Thermostat device."""

    # It can remove from HA >= 2025.1
    # see https://developers.home-assistant.io/blog/2024/01/24/climate-climateentityfeatures-expanded/
    _enable_turn_on_off_backwards_compatibility = False

    _last_on_mode: HVACMode | None

    def __init__(
        self,
        hass,
        vendor,
        config,
    ):
        """Initialize the thermostat."""
        self.topic = config.get(CONF_COMMAND_TOPIC)
        self.hass = hass
        self._vendor = vendor
        self._temp_sensor = config.get(CONF_TEMP_SENSOR)
        self._humidity_sensor = config.get(CONF_HUMIDITY_SENSOR)
        self._power_sensor = config.get(CONF_POWER_SENSOR)
        self.state_topic = config[CONF_STATE_TOPIC]
        self.state_topic2 = config.get(CONF_STATE_TOPIC + "_2")
        self._away_temp = config.get(CONF_AWAY_TEMP)
        self._saved_target_temp = config[CONF_TARGET_TEMP] or self._away_temp
        self._temp_precision = config[CONF_PRECISION]
        self._enabled = False
        self.power_mode = None
        self._active = False
        self._mqtt_delay = config[CONF_MQTT_DELAY]
        self._min_temp = config[CONF_MIN_TEMP]
        self._max_temp = config[CONF_MAX_TEMP]
        self._def_target_temp = config[CONF_TARGET_TEMP]
        self._is_away = False
        self._modes_list = config[CONF_MODES_LIST]
        self._quiet = config[CONF_QUIET].lower()
        self._turbo = config[CONF_TURBO].lower()
        self._econo = config[CONF_ECONO].lower()
        self._model = config[CONF_MODEL]
        self._celsius = config[CONF_CELSIUS]
        self._light = config[CONF_LIGHT].lower()
        self._filter = config[CONF_FILTER].lower()
        self._clean = config[CONF_CLEAN].lower()
        self._beep = config[CONF_BEEP].lower()
        self._sleep = config[CONF_SLEEP].lower()
        self._sub_state = None
        self._keep_mode = config[CONF_KEEP_MODE]
        self._last_on_mode = None
        self._swingv = (
            config.get(CONF_SWINGV).lower()
            if config.get(CONF_SWINGV) is not None
            else None
        )
        self._swingh = (
            config.get(CONF_SWINGH).lower()
            if config.get(CONF_SWINGH) is not None
            else None
        )
        self._fix_swingv = None
        self._fix_swingh = None
        self._toggle_list = config[CONF_TOGGLE_LIST]
        self._state_mode = DEFAULT_STATE_MODE
        self._ignore_off_temp = config[CONF_IGNORE_OFF_TEMP]
        self._use_track_state_change_event = False
        self._unsubscribes = []

        self.availability_topic = config.get(CONF_AVAILABILITY_TOPIC)
        if (self.availability_topic) is None:
            path = self.topic.split("/")
            self.availability_topic = "tele/" + path[1] + "/LWT"

        # Set _attr_*
        self._attr_unique_id = config.get(CONF_UNIQUE_ID)
        self._attr_name = config.get(CONF_NAME)
        self._attr_should_poll = False
        self._attr_temperature_unit = (
            UnitOfTemperature.CELSIUS
            if self._celsius.lower() == "on"
            else UnitOfTemperature.FAHRENHEIT
        )
        self._attr_hvac_mode = config.get(CONF_INITIAL_OPERATION_MODE)
        self._attr_target_temperature_step = config[CONF_TEMP_STEP]
        self._attr_hvac_modes = config[CONF_MODES_LIST]
        self._attr_fan_modes = config.get(CONF_FAN_LIST)
        if (
            isinstance(self._attr_fan_modes, list)
            and HVAC_FAN_MAX_HIGH in self._attr_fan_modes
            and HVAC_FAN_AUTO_MAX in self._attr_fan_modes
        ):
            new_fan_list = []
            for val in self._attr_fan_modes:
                if val == HVAC_FAN_MAX_HIGH:
                    new_fan_list.append(FAN_HIGH)
                elif val == HVAC_FAN_AUTO_MAX:
                    new_fan_list.append(HVAC_FAN_MAX)
                else:
                    new_fan_list.append(val)
            self._attr_fan_modes = new_fan_list if len(new_fan_list) else None
        self._attr_fan_mode = (
            self._attr_fan_modes[0] if isinstance(self._attr_fan_modes, list) else None
        )
        self._attr_swing_modes = config.get(CONF_SWING_LIST)
        self._attr_swing_mode = (
            self._attr_swing_modes[0]
            if isinstance(self._attr_swing_modes, list)
            else None
        )
        self._attr_preset_modes = (
            [PRESET_NONE, PRESET_AWAY] if self._away_temp else None
        )
        self._attr_preset_mode = None
        self._attr_current_temperature = None
        self._attr_current_humidity = None
        self._attr_target_temperature = None

        self._support_flags = SUPPORT_FLAGS
        if self._away_temp is not None:
            self._support_flags = self._support_flags | ClimateEntityFeature.PRESET_MODE
        if self._attr_swing_mode is not None:
            self._support_flags = self._support_flags | ClimateEntityFeature.SWING_MODE

    async def async_added_to_hass(self):
        # Replacing `async_track_state_change` with `async_track_state_change_event`
        # See, https://developers.home-assistant.io/blog/2024/04/13/deprecate_async_track_state_change/
        if hasattr(ha_event, "async_track_state_change_event"):
            self._use_track_state_change_event = True

        def regist_track_state_change_event(entity_id):
            if self._use_track_state_change_event:
                ha_event.async_track_state_change_event(
                    self.hass, entity_id, self._async_sensor_changed
                )
            else:
                ha_event.async_track_state_change(
                    self.hass, entity_id, self._async_sensor_changed
                )

        # Make sure MQTT integration is enabled and the client is available
        await mqtt.async_wait_for_mqtt_client(self.hass)

        """Run when entity about to be added."""
        await super().async_added_to_hass()

        # Add listener
        self._unsubscribes = await self._subscribe_topics()

        # Check If we have an old state
        old_state = await self.async_get_last_state()
        if old_state is not None:
            # If we have no initial temperature, restore
            if old_state.attributes.get(ATTR_TEMPERATURE) is not None:
                self._attr_target_temperature = float(
                    old_state.attributes[ATTR_TEMPERATURE]
                )
            if old_state.attributes.get(ATTR_PRESET_MODE) == PRESET_AWAY:
                self._is_away = True
            if old_state.attributes.get(ATTR_FAN_MODE) is not None:
                self._attr_fan_mode = old_state.attributes.get(ATTR_FAN_MODE)
            if old_state.attributes.get(ATTR_SWING_MODE) is not None:
                self._attr_swing_mode = old_state.attributes.get(ATTR_SWING_MODE)
            if old_state.attributes.get(ATTR_LAST_ON_MODE) is not None:
                self._last_on_mode = old_state.attributes.get(ATTR_LAST_ON_MODE)

            for attr, prop in ATTRIBUTES_IRHVAC.items():
                val = old_state.attributes.get(attr)
                if val is not None:
                    setattr(self, "_" + prop, val)
            if old_state.state:
                self._attr_hvac_mode = (
                    HVACMode.OFF
                    if old_state.state in [STATE_UNKNOWN, STATE_UNAVAILABLE]
                    else HVACMode.OFF  # old_state.state
                )
                self._enabled = self._attr_hvac_mode != HVACMode.OFF
                if self._enabled:
                    self._last_on_mode = self._attr_hvac_mode
            if self._swingv != "auto":
                self._fix_swingv = self._swingv
            if self._swingh != "auto":
                self._fix_swingh = self._swingh

        # No previous target temperature, try and restore defaults
        if self._attr_target_temperature is None or self._attr_target_temperature < 1:
            self._attr_target_temperature = self._def_target_temp
            _LOGGER.warning(
                "No previously saved target temperature, setting to default value %s",
                self._attr_target_temperature,
            )

        if self._attr_hvac_mode is HVACMode.OFF:
            self.power_mode = STATE_OFF
            self._enabled = False
        else:
            self.power_mode = STATE_ON
            self._enabled = True

        for key in self._toggle_list:
            setattr(self, "_" + key.lower(), "off")

        if self._temp_sensor:
            regist_track_state_change_event(self._temp_sensor)

            temp_sensor_state = self.hass.states.get(self._temp_sensor)
            if (
                temp_sensor_state
                and temp_sensor_state.state != STATE_UNKNOWN
                and temp_sensor_state.state != STATE_UNAVAILABLE
            ):
                self._async_update_temp(temp_sensor_state)

        if self._humidity_sensor:
            regist_track_state_change_event(self._humidity_sensor)

            humidity_sensor_state = self.hass.states.get(self._humidity_sensor)
            if (
                humidity_sensor_state
                and humidity_sensor_state.state != STATE_UNKNOWN
                and humidity_sensor_state.state != STATE_UNAVAILABLE
            ):
                self._async_update_humidity(humidity_sensor_state)

        if self._power_sensor:
            regist_track_state_change_event(self._power_sensor)

    async def _subscribe_topics(self):
        """(Re)Subscribe to topics."""

        @callback
        async def available_message_received(message: mqtt.ReceiveMessage) -> None:
            msg = message.payload
            _LOGGER.debug(msg)
            if msg == "Online" or msg == "Offline":
                self._attr_available = True if msg == "Online" else False
                self.async_schedule_update_ha_state()

        @callback
        async def state_message_received(message: mqtt.ReceiveMessage) -> None:
            """Handle new MQTT state messages."""
            json_payload = json.loads(message.payload)
            _LOGGER.debug(json_payload)

            # If listening to `tele`, result looks like: {"IrReceived":{"Protocol":"XXX", ... ,"IRHVAC":{ ... }}}
            # we want to extract the data.
            if "IrReceived" in json_payload:
                json_payload = json_payload["IrReceived"]

            # By now the payload must include an `IRHVAC` field.
            if "IRHVAC" not in json_payload:
                return

            payload = json_payload["IRHVAC"]

            if payload["Vendor"] == self._vendor:
                # All values in the payload are Optional
                prev_power = self.power_mode
                if "Power" in payload:
                    self.power_mode = payload["Power"].lower()
                if "Mode" in payload:
                    self._attr_hvac_mode = payload["Mode"].lower()
                    # Some vendors send/receive mode as fan instead of fan_only
                    if self._attr_hvac_mode == HVACAction.FAN:
                        self._attr_hvac_mode = HVACMode.FAN_ONLY
                if "Temp" in payload:
                    if payload["Temp"] > 0:
                        if self.power_mode == STATE_OFF and self._ignore_off_temp:
                            self._attr_target_temperature = (
                                self._attr_target_temperature
                            )
                        else:
                            self._attr_target_temperature = payload["Temp"]
                if "Celsius" in payload:
                    self._celsius = payload["Celsius"].lower()
                if "Quiet" in payload:
                    self._quiet = payload["Quiet"].lower()
                if "Turbo" in payload:
                    self._turbo = payload["Turbo"].lower()
                if "Econo" in payload:
                    self._econo = payload["Econo"].lower()
                if "Light" in payload:
                    self._light = payload["Light"].lower()
                if "Filter" in payload:
                    self._filter = payload["Filter"].lower()
                if "Clean" in payload:
                    self._clean = payload["Clean"].lower()
                if "Beep" in payload:
                    self._beep = payload["Beep"].lower()
                if "Sleep" in payload:
                    self._sleep = payload["Sleep"]
                if "SwingV" in payload:
                    self._swingv = payload["SwingV"].lower()
                    if self._swingv != "auto":
                        self._fix_swingv = self._swingv
                if "SwingH" in payload:
                    self._swingh = payload["SwingH"].lower()
                    if self._swingh != "auto":
                        self._fix_swingh = self._swingh
                if (
                    "SwingV" in payload
                    and payload["SwingV"].lower() == STATE_AUTO
                    and "SwingH" in payload
                    and payload["SwingH"].lower() == STATE_AUTO
                ):
                    if SWING_BOTH in (self._attr_swing_modes or []):
                        self._attr_swing_mode = SWING_BOTH
                    elif SWING_VERTICAL in (self._attr_swing_modes or []):
                        self._attr_swing_mode = SWING_VERTICAL
                    elif SWING_HORIZONTAL in (self._attr_swing_modes or []):
                        self._attr_swing_mode = SWING_HORIZONTAL
                    else:
                        self._attr_swing_mode = SWING_OFF
                elif (
                    "SwingV" in payload
                    and payload["SwingV"].lower() == STATE_AUTO
                    and SWING_VERTICAL in (self._attr_swing_modes or [])
                ):
                    self._attr_swing_mode = SWING_VERTICAL
                elif (
                    "SwingH" in payload
                    and payload["SwingH"].lower() == STATE_AUTO
                    and SWING_HORIZONTAL in (self._attr_swing_modes or [])
                ):
                    self._attr_swing_mode = SWING_HORIZONTAL
                else:
                    self._attr_swing_mode = SWING_OFF

                if "FanSpeed" in payload:
                    fan_mode = payload["FanSpeed"].lower()
                    # ELECTRA_AC fan modes fix
                    if HVAC_FAN_MAX_HIGH in (
                        self._attr_fan_modes or []
                    ) and HVAC_FAN_AUTO_MAX in (self._attr_fan_modes or []):
                        if fan_mode == HVAC_FAN_MAX:
                            self._attr_fan_mode = FAN_HIGH
                        elif fan_mode == HVAC_FAN_AUTO:
                            self._attr_fan_mode = HVAC_FAN_MAX
                        else:
                            self._attr_fan_mode = fan_mode
                    else:
                        self._attr_fan_mode = fan_mode
                    _LOGGER.debug(self._attr_fan_mode)

                if self._attr_hvac_mode is not HVACMode.OFF:
                    self._last_on_mode = self._attr_hvac_mode

                # Set default state to off
                if self.power_mode == STATE_OFF:
                    self._attr_hvac_mode = HVACMode.OFF
                    self._enabled = False
                else:
                    self._enabled = True

                # Set toggles to 'off'
                for key in self._toggle_list:
                    setattr(self, "_" + key.lower(), "off")

                # Update HA UI and State
                self.async_schedule_update_ha_state()

                # Check power sensor state
                if (
                    self._power_sensor
                    and prev_power is not None
                    and prev_power != self.power_mode
                ):
                    await asyncio.sleep(3)
                    state = self.hass.states.get(self._power_sensor)
                    await self._async_power_sensor_changed(None, state)

        unsubscribe = []
        unsubscribe.append(
            await mqtt.async_subscribe(
                self.hass, self.state_topic, state_message_received
            )
        )
        unsubscribe.append(
            await mqtt.async_subscribe(
                self.hass, self.availability_topic, available_message_received
            )
        )
        if self.state_topic2:
            unsubscribe.append(
                await mqtt.async_subscribe(
                    self.hass, self.state_topic2, state_message_received
                )
            )

        return unsubscribe

    async def async_will_remove_from_hass(self):
        """Unsubscribe when removed."""
        for unsubscribe in self._unsubscribes:
            unsubscribe()

    @property
    def precision(self):
        """Return the precision of the system."""
        if self._temp_precision is not None:
            return self._temp_precision
        return super().precision

    # This extension property is written throughout the instance, so use @property instead of @cached_property.
    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported.

        Need to be one of CURRENT_HVAC_*.
        """
        if self._attr_hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        elif self._attr_hvac_mode == HVACMode.HEAT:
            return HVACAction.HEATING
        elif self._attr_hvac_mode == HVACMode.COOL:
            return HVACAction.COOLING
        elif self._attr_hvac_mode == HVACMode.DRY:
            return HVACAction.DRYING
        elif self._attr_hvac_mode == HVACMode.FAN_ONLY:
            return HVACAction.FAN

    # This extension property is written throughout the instance, so use @property instead of @cached_property.
    @property
    def extra_state_attributes(self):
        """Return the state attributes of the device."""
        return {
            attr: getattr(self, "_" + prop) for attr, prop in ATTRIBUTES_IRHVAC.items()
        }

    @property
    def last_on_mode(self):
        """Return the last non-idle mode ie. heat, cool."""
        return self._last_on_mode

    async def async_set_hvac_mode(self, hvac_mode):
        """Set hvac mode."""
        await self.set_mode(hvac_mode)
        # Ensure we update the current operation after changing the mode
        await self.async_send_cmd()

    async def async_turn_on(self):
        """Turn thermostat on."""
        self._attr_hvac_mode = (
            self._last_on_mode if self._last_on_mode is not None else HVACMode.AUTO
        )
        self.power_mode = STATE_ON
        await self.async_send_cmd()

    async def async_turn_off(self):
        """Turn thermostat off."""
        self._attr_hvac_mode = HVACMode.OFF
        self.power_mode = STATE_OFF
        await self.async_send_cmd()

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        hvac_mode = kwargs.get(ATTR_HVAC_MODE)
        if temperature is None:
            return

        if hvac_mode is not None:
            await self.set_mode(hvac_mode)

        self._attr_target_temperature = temperature
        if not self._attr_hvac_mode == HVACMode.OFF:
            self.power_mode = STATE_ON
        await self.async_send_cmd()

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        if fan_mode not in (self._attr_fan_modes or []):
            # tweak for some ELECTRA_AC devices
            if HVAC_FAN_MAX_HIGH in (
                self._attr_fan_modes or []
            ) and HVAC_FAN_AUTO_MAX in (self._attr_fan_modes or []):
                if fan_mode != FAN_HIGH and fan_mode != HVAC_FAN_MAX:
                    _LOGGER.error(
                        "Invalid swing mode selected. Got '%s'. Allowed modes are:",
                        fan_mode,
                    )
                    _LOGGER.error(self._attr_fan_modes)
                    return
            else:
                _LOGGER.error(
                    "Invalid swing mode selected. Got '%s'. Allowed modes are:",
                    fan_mode,
                )
                _LOGGER.error(self._attr_fan_modes)
                return
        self._attr_fan_mode = fan_mode
        if not self._attr_hvac_mode == HVACMode.OFF:
            self.power_mode = STATE_ON
        await self.async_send_cmd()

    async def async_set_swing_mode(self, swing_mode):
        """Set new target swing operation."""
        if swing_mode not in (self._attr_swing_modes or []):
            _LOGGER.error(
                "Invalid swing mode selected. Got '%s'. Allowed modes are:", swing_mode
            )
            _LOGGER.error(self._attr_swing_modes)
            return
        self._attr_swing_mode = swing_mode
        # note: set _swingv and _swingh in send_ir() later
        if not self._attr_hvac_mode == HVACMode.OFF:
            self.power_mode = STATE_ON
        await self.async_send_cmd()

    async def async_set_econo(self, econo, state_mode):
        """Set new target econo mode."""
        if econo not in ON_OFF_LIST:
            return
        self._econo = econo.lower()
        self._state_mode = state_mode
        await self.async_send_cmd()

    async def async_set_turbo(self, turbo, state_mode):
        """Set new target turbo mode."""
        if turbo not in ON_OFF_LIST:
            return
        self._turbo = turbo.lower()
        self._state_mode = state_mode
        await self.async_send_cmd()

    async def async_set_quiet(self, quiet, state_mode):
        """Set new target quiet mode."""
        if quiet not in ON_OFF_LIST:
            return
        self._quiet = quiet.lower()
        self._state_mode = state_mode
        await self.async_send_cmd()

    async def async_set_light(self, light, state_mode):
        """Set new target light mode."""
        if light not in ON_OFF_LIST:
            return
        self._light = light.lower()
        self._state_mode = state_mode
        await self.async_send_cmd()

    async def async_set_filters(self, filters, state_mode):
        """Set new target filters mode."""
        if filters not in ON_OFF_LIST:
            return
        self._filter = filters.lower()
        self._state_mode = state_mode
        await self.async_send_cmd()

    async def async_set_clean(self, clean, state_mode):
        """Set new target clean mode."""
        if clean not in ON_OFF_LIST:
            return
        self._clean = clean.lower()
        self._state_mode = state_mode
        await self.async_send_cmd()

    async def async_set_beep(self, beep, state_mode):
        """Set new target beep mode."""
        if beep not in ON_OFF_LIST:
            return
        self._beep = beep.lower()
        self._state_mode = state_mode
        await self.async_send_cmd()

    async def async_set_sleep(self, sleep, state_mode):
        """Set new target sleep mode."""
        self._sleep = sleep.lower()
        self._state_mode = state_mode
        await self.async_send_cmd()

    async def async_set_swingv(self, swingv, state_mode):
        """Set new target swingv."""
        self._swingv = swingv.lower()
        if self._swingv != "auto":
            self._fix_swingv = self._swingv
            if self._attr_swing_mode == SWING_BOTH:
                if SWING_HORIZONTAL in (self._attr_swing_modes or []):
                    self._attr_swing_mode = SWING_HORIZONTAL
            elif self._attr_swing_mode == SWING_VERTICAL:
                self._attr_swing_mode = SWING_OFF
        else:
            if self._attr_swing_mode == SWING_HORIZONTAL:
                if SWING_BOTH in (self._attr_swing_modes or []):
                    self._attr_swing_mode = SWING_BOTH
            else:
                if SWING_VERTICAL in (self._attr_swing_modes or []):
                    self._attr_swing_mode = SWING_VERTICAL
        self._state_mode = state_mode
        await self.async_send_cmd()

    async def async_set_swingh(self, swingh, state_mode):
        """Set new target swingh."""
        self._swingh = swingh.lower()
        if self._swingh != "auto":
            self._fix_swingh = self._swingh
            if self._attr_swing_mode == SWING_BOTH:
                if SWING_VERTICAL in (self._attr_swing_modes or []):
                    self._attr_swing_mode = SWING_VERTICAL
            elif self._attr_swing_mode == SWING_HORIZONTAL:
                self._attr_swing_mode = SWING_OFF
        else:
            if self._attr_swing_mode == SWING_VERTICAL:
                if SWING_BOTH in (self._attr_swing_modes or []):
                    self._attr_swing_mode = SWING_BOTH
            else:
                if SWING_HORIZONTAL in (self._attr_swing_modes or []):
                    self._attr_swing_mode = SWING_HORIZONTAL
        self._state_mode = state_mode
        await self.async_send_cmd()

    async def async_send_cmd(self):
        await self.send_ir()

    @cached_property
    def min_temp(self):
        """Return the minimum temperature."""
        if self._min_temp:
            return self._min_temp

        # get default temp from super class
        return super().min_temp

    @cached_property
    def max_temp(self):
        """Return the maximum temperature."""
        if self._max_temp:
            return self._max_temp

        # Get default temp from super class
        return super().max_temp

    async def _async_sensor_changed(
        self, entity_id_or_event, old_state=None, new_state=None
    ):
        # Replacing `async_track_state_change` with `async_track_state_change_event`
        # See, https://developers.home-assistant.io/blog/2024/04/13/deprecate_async_track_state_change/
        if self._use_track_state_change_event:
            entity_id = entity_id_or_event.data["entity_id"]
            old_state = entity_id_or_event.data["old_state"]
            new_state = entity_id_or_event.data["new_state"]
        else:
            entity_id = entity_id_or_event

        if new_state is None:
            return

        if entity_id == self._temp_sensor:
            self._async_update_temp(new_state)
            self.async_schedule_update_ha_state()
        elif entity_id == self._humidity_sensor:
            self._async_update_humidity(new_state)
            self.async_schedule_update_ha_state()
        elif entity_id == self._power_sensor:
            await self._async_power_sensor_changed(old_state, new_state)

    async def _async_power_sensor_changed(self, old_state, new_state):
        """Handle power sensor changes."""
        if new_state is None:
            return

        if old_state is not None and new_state.state == old_state.state:
            return

        if new_state.state == STATE_ON:
            if self._attr_hvac_mode == HVACMode.OFF or self.power_mode == STATE_OFF:
                self._attr_hvac_mode = self._last_on_mode
                self.power_mode = STATE_ON
                self.async_schedule_update_ha_state()

        elif new_state.state == STATE_OFF:
            if self._attr_hvac_mode != HVACMode.OFF or self.power_mode == STATE_ON:
                self._attr_hvac_mode = HVACMode.OFF
                self.power_mode = STATE_OFF
                self.async_schedule_update_ha_state()

    @callback
    def _async_update_temp(self, state):
        """Update thermostat with latest state from sensor."""
        try:
            self._attr_current_temperature = float(state.state)
        except ValueError as ex:
            _LOGGER.debug("Unable to update from sensor: %s", ex)

    @callback
    def _async_update_humidity(self, state):
        """Update thermostat with latest state from humidity sensor."""
        try:
            if state.state != STATE_UNKNOWN and state.state != STATE_UNAVAILABLE:
                self._attr_current_humidity = int(float(state.state))
        except ValueError as ex:
            _LOGGER.error("Unable to update from humidity sensor: %s", ex)

    @property
    def _is_device_active(self):
        """If the toggleable device is currently active."""
        return self.power_mode == STATE_ON

    @cached_property
    def supported_features(self):
        """Return the list of supported features."""
        return self._support_flags

    async def async_set_preset_mode(self, preset_mode):
        """Set new preset mode.

        This method must be run in the event loop and returns a coroutine.
        """
        if preset_mode == PRESET_AWAY and not self._is_away:
            self._is_away = True
            self._saved_target_temp = self._attr_target_temperature
            self._attr_target_temperature = self._away_temp
        elif preset_mode == PRESET_NONE and self._is_away:
            self._is_away = False
            self._attr_target_temperature = self._saved_target_temp
        self._attr_preset_mode = PRESET_AWAY if self._is_away else PRESET_NONE
        await self.send_ir()

    async def set_mode(self, hvac_mode):
        """Set hvac mode."""
        hvac_mode = hvac_mode.lower()
        if hvac_mode not in self._attr_hvac_modes or hvac_mode == HVACMode.OFF:
            self._attr_hvac_mode = HVACMode.OFF
            self._enabled = False
            self.power_mode = STATE_OFF
        else:
            self._attr_hvac_mode = self._last_on_mode = hvac_mode
            self._enabled = True
            self.power_mode = STATE_ON

    async def send_ir(self):
        """Send the payload to tasmota mqtt topic."""
        fan_speed = self.fan_mode
        # tweak for some ELECTRA_AC devices
        if HVAC_FAN_MAX_HIGH in (self._attr_fan_modes or []) and HVAC_FAN_AUTO_MAX in (
            self._attr_fan_modes or []
        ):
            if self.fan_mode == FAN_HIGH:
                fan_speed = HVAC_FAN_MAX
            if self.fan_mode == HVAC_FAN_MAX:
                fan_speed = HVAC_FAN_AUTO

        # Set the swing mode - default off
        self._swingv = STATE_OFF if self._fix_swingv is None else self._fix_swingv
        self._swingh = STATE_OFF if self._fix_swingh is None else self._fix_swingh

        if SWING_BOTH in (self._attr_swing_modes or []) or SWING_VERTICAL in (
            self._attr_swing_modes or []
        ):
            if (
                self._attr_swing_mode == SWING_BOTH
                or self._attr_swing_mode == SWING_VERTICAL
            ):
                self._swingv = STATE_AUTO

        if SWING_BOTH in (self._attr_swing_modes or []) or SWING_HORIZONTAL in (
            self._attr_swing_modes or []
        ):
            if (
                self._attr_swing_mode == SWING_BOTH
                or self._attr_swing_mode == SWING_HORIZONTAL
            ):
                self._swingh = STATE_AUTO

        _dt = dt_util.now()
        _min = _dt.hour * 60 + _dt.minute

        # Populate the payload
        payload_data = {
            "StateMode": self._state_mode,
            "Vendor": self._vendor,
            "Model": self._model,
            "Power": self.power_mode,
            "Mode": self._last_on_mode if self._keep_mode else self._attr_hvac_mode,
            "Celsius": self._celsius,
            "Temp": self._attr_target_temperature,
            "FanSpeed": fan_speed,
            "SwingV": self._swingv,
            "SwingH": self._swingh,
            "Quiet": self._quiet,
            "Turbo": self._turbo,
            "Econo": self._econo,
            "Light": self._light,
            "Filter": self._filter,
            "Clean": self._clean,
            "Beep": self._beep,
            "Sleep": self._sleep,
            "Clock": int(_min),
            "Weekday": int(_dt.weekday()),
        }
        self._state_mode = DEFAULT_STATE_MODE
        for key in self._toggle_list:
            setattr(self, "_" + key.lower(), "off")

        payload = json.dumps(payload_data)

        # Publish mqtt message
        if float(self._mqtt_delay) != float(DEFAULT_MQTT_DELAY):
            await asyncio.sleep(float(self._mqtt_delay))

        await mqtt.async_publish(self.hass, self.topic, payload)

        # Update HA UI and State
        self.async_schedule_update_ha_state()
