"""Adds support for generic thermostat units."""
import json
import logging
import uuid
import asyncio
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util

from homeassistant.components import mqtt
from homeassistant.components.mqtt.mixins import (
    MqttAvailability,
    MQTT_AVAILABILITY_SCHEMA,
    CONF_AVAILABILITY_TOPIC,
)
from homeassistant.components.climate import PLATFORM_SCHEMA
try:
    from homeassistant.components.climate import ClimateEntity
except ImportError:
    from homeassistant.components.binary_sensor import ClimateDevice as ClimateEntity
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change
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
    HVAC_MODE_DRY,
    ATTR_PRESET_MODE,
    ATTR_FAN_MODE,
    ATTR_SWING_MODE,
    ATTR_HVAC_MODE,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_COOL,
    CURRENT_HVAC_DRY,
    CURRENT_HVAC_FAN,
    CURRENT_HVAC_OFF,
    PRESET_AWAY,
    PRESET_NONE,
    SUPPORT_FAN_MODE,
    SUPPORT_SWING_MODE,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
    SWING_BOTH,
    SWING_HORIZONTAL,
    SWING_OFF,
    SWING_VERTICAL
)

from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    CONF_NAME,
    CONF_UNIQUE_ID,
    EVENT_HOMEASSISTANT_START,
    PRECISION_HALVES,
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    STATE_ON,
    STATE_OFF,
    STATE_UNKNOWN,
    STATE_UNAVAILABLE,
)

from .const import (
    ATTR_VALUE,
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
    ATTRIBUTES_IRHVAC,
    STATE_AUTO,
    STATE_COOL,
    STATE_DRY,
    STATE_FAN_ONLY,
    STATE_HEAT,
    HVAC_FAN_AUTO,
    HVAC_FAN_MIN,
    HVAC_FAN_MEDIUM,
    HVAC_FAN_MAX,
    HVAC_MODE_AUTO_FAN,
    HVAC_MODE_FAN_AUTO,
    HVAC_FAN_MAX_HIGH,
    HVAC_FAN_AUTO_MAX,
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_AUTO,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODES,
    CONF_EXCLUSIVE_GROUP_VENDOR,
    CONF_VENDOR,
    CONF_PROTOCOL,
    CONF_COMMAND_TOPIC,
    CONF_STATE_TOPIC,
    CONF_TEMP_SENSOR,
    CONF_HUMIDITY_SENSOR,
    CONF_POWER_SENSOR,
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
    DATA_KEY,
    DOMAIN,
    DEFAULT_NAME,
    DEFAULT_STATE_TOPIC,
    DEFAULT_COMMAND_TOPIC,
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
    ON_OFF_LIST,
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
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT,
    HVAC_MODE_DRY,
    HVAC_MODE_AUTO_FAN,
    HVAC_MODE_FAN_AUTO,
]

DEFAULT_SWING_LIST = [SWING_OFF, SWING_VERTICAL]
DEFAULT_INITIAL_OPERATION_MODE = HVAC_MODE_OFF

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = (
    SUPPORT_TARGET_TEMPERATURE
    | SUPPORT_FAN_MODE
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
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
        vol.Optional(CONF_MAX_TEMP, default=DEFAULT_MAX_TEMP): vol.Coerce(float),
        vol.Optional(CONF_MIN_TEMP, default=DEFAULT_MIN_TEMP): vol.Coerce(float),
        vol.Optional(CONF_TARGET_TEMP, default=DEFAULT_TARGET_TEMP): vol.Coerce(float),
        vol.Optional(
            CONF_INITIAL_OPERATION_MODE, default=DEFAULT_INITIAL_OPERATION_MODE
        ): vol.In(
            HVAC_MODES
        ),
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
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(MQTT_AVAILABILITY_SCHEMA.schema)
if hasattr(mqtt, 'MQTT_BASE_PLATFORM_SCHEMA'):
    PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(mqtt.MQTT_BASE_PLATFORM_SCHEMA.schema)
else:
    PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(mqtt.config.MQTT_BASE_SCHEMA.schema)

IRHVAC_SERVICE_SCHEMA = vol.Schema(
    {vol.Required(ATTR_ENTITY_ID): cv.entity_ids})

SERVICE_SCHEMA_ECONO_MODE = IRHVAC_SERVICE_SCHEMA.extend(
    {vol.Required(ATTR_ECONO): vol.In(ON_OFF_LIST)}
)
SERVICE_SCHEMA_TURBO_MODE = IRHVAC_SERVICE_SCHEMA.extend(
    {vol.Required(ATTR_TURBO): vol.In(ON_OFF_LIST)}
)
SERVICE_SCHEMA_QUIET_MODE = IRHVAC_SERVICE_SCHEMA.extend(
    {vol.Required(ATTR_QUIET): vol.In(ON_OFF_LIST)}
)
SERVICE_SCHEMA_LIGHT_MODE = IRHVAC_SERVICE_SCHEMA.extend(
    {vol.Required(ATTR_LIGHT): vol.In(ON_OFF_LIST)}
)
SERVICE_SCHEMA_FILTERS_MODE = IRHVAC_SERVICE_SCHEMA.extend(
    {vol.Required(ATTR_FILTERS): vol.In(ON_OFF_LIST)}
)
SERVICE_SCHEMA_CLEAN_MODE = IRHVAC_SERVICE_SCHEMA.extend(
    {vol.Required(ATTR_CLEAN): vol.In(ON_OFF_LIST)}
)
SERVICE_SCHEMA_BEEP_MODE = IRHVAC_SERVICE_SCHEMA.extend(
    {vol.Required(ATTR_BEEP): vol.In(ON_OFF_LIST)}
)
SERVICE_SCHEMA_SLEEP_MODE = IRHVAC_SERVICE_SCHEMA.extend(
    {vol.Required(ATTR_SLEEP): cv.string}
)
SERVICE_SCHEMA_SET_SWINGV = IRHVAC_SERVICE_SCHEMA.extend(
    {vol.Required(ATTR_SWINGV): vol.In(['off', 'auto', 'highest', 'high', 'middle', 'low', 'lowest'])}
)
SERVICE_SCHEMA_SET_SWINGH = IRHVAC_SERVICE_SCHEMA.extend(
    {vol.Required(ATTR_SWINGH): vol.In(['off', 'auto', 'left max', 'left', 'middle', 'right', 'right max', 'wide'])}
)

SERVICE_TO_METHOD = {
    SERVICE_ECONO_MODE: {
        'method': 'async_set_econo',
        'schema': SERVICE_SCHEMA_ECONO_MODE,
    },
    SERVICE_TURBO_MODE: {
        'method': 'async_set_turbo',
        'schema': SERVICE_SCHEMA_TURBO_MODE,
    },
    SERVICE_QUIET_MODE: {
        'method': 'async_set_quiet',
        'schema': SERVICE_SCHEMA_QUIET_MODE,
    },
    SERVICE_LIGHT_MODE: {
        'method': 'async_set_light',
        'schema': SERVICE_SCHEMA_LIGHT_MODE,
    },
    SERVICE_FILTERS_MODE: {
        'method': 'async_set_filters',
        'schema': SERVICE_SCHEMA_FILTERS_MODE,
    },
    SERVICE_CLEAN_MODE: {
        'method': 'async_set_clean',
        'schema': SERVICE_SCHEMA_CLEAN_MODE,
    },
    SERVICE_BEEP_MODE: {
        'method': 'async_set_beep',
        'schema': SERVICE_SCHEMA_BEEP_MODE,
    },
    SERVICE_SLEEP_MODE: {
        'method': 'async_set_sleep',
        'schema': SERVICE_SCHEMA_SLEEP_MODE
    },
    SERVICE_SET_SWINGV: {
        'method': 'async_set_swingv',
        'schema': SERVICE_SCHEMA_SET_SWINGV
    },
    SERVICE_SET_SWINGH: {
        'method': 'async_set_swingh',
        'schema': SERVICE_SCHEMA_SET_SWINGH
    },
}


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the generic thermostat platform."""
    vendor = config.get(CONF_VENDOR)
    protocol = config.get(CONF_PROTOCOL)

    if DATA_KEY not in hass.data:
        hass.data[DATA_KEY] = {}

    if vendor is None:
        if protocol is None:
            _LOGGER.error(
                'Neither vendor nor protocol provided for "%s"!', name)
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
        method = SERVICE_TO_METHOD.get(service.service)
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
            update_tasks.append(device.async_update_ha_state(True))

        if update_tasks:
            await asyncio.wait(update_tasks)

    for irhvac_service in SERVICE_TO_METHOD:
        schema = SERVICE_TO_METHOD[irhvac_service].get(
            "schema", IRHVAC_SERVICE_SCHEMA
        )
        hass.services.async_register(
            DOMAIN, irhvac_service, async_service_handler, schema=schema
        )


class TasmotaIrhvac(ClimateEntity, RestoreEntity, MqttAvailability):
    """Representation of a Generic Thermostat device."""

    def __init__(
        self,
        hass,
        vendor,
        config,
    ):
        """Initialize the thermostat."""
        self._unique_id = config.get(CONF_UNIQUE_ID)
        self.topic = config.get(CONF_COMMAND_TOPIC)
        self.hass = hass
        self._vendor = vendor
        self._name = config.get(CONF_NAME)
        self._temp_sensor = config.get(CONF_TEMP_SENSOR)
        self._humidity_sensor = config.get(CONF_HUMIDITY_SENSOR)
        self._power_sensor = config.get(CONF_POWER_SENSOR)
        self.state_topic = config[CONF_STATE_TOPIC]
        self._hvac_mode = config[CONF_INITIAL_OPERATION_MODE]
        self._away_temp = config.get(CONF_AWAY_TEMP)
        self._saved_target_temp = config[CONF_TARGET_TEMP] or self._away_temp
        self._temp_precision = config[CONF_PRECISION]
        self._temp_step = config[CONF_TEMP_STEP]
        self._hvac_list = config[CONF_MODES_LIST]
        self._fan_list = config[CONF_FAN_LIST]
        self._fan_mode = self._fan_list[0]
        self._swing_list = config[CONF_SWING_LIST]
        self._swing_mode = self._swing_list[0] if len(self._swing_list) > 0 else None
        self._enabled = False
        self.power_mode = None
        self._active = False
        self._cur_temp = None
        self._min_temp = config[CONF_MIN_TEMP]
        self._max_temp = config[CONF_MAX_TEMP]
        self._cur_humidity = None
        self._target_temp = None
        self._def_target_temp = config[CONF_TARGET_TEMP]
        self._unit = hass.config.units.temperature_unit
        self._support_flags = SUPPORT_FLAGS
        if self._away_temp is not None:
            self._support_flags = self._support_flags | SUPPORT_PRESET_MODE
        if self._swing_mode is not None:
            self._support_flags = self._support_flags | SUPPORT_SWING_MODE
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
        self._swingv = config.get(CONF_SWINGV).lower() if config.get(CONF_SWINGV) is not None else None
        self._swingh = config.get(CONF_SWINGH).lower() if config.get(CONF_SWINGH) is not None else None
        self._fix_swingv = None
        self._fix_swingh = None
        self._toggle_list = config[CONF_TOGGLE_LIST]

        availability_topic = config.get(CONF_AVAILABILITY_TOPIC)
        if (availability_topic) is None:
            path = self.topic.split('/')
            availability_topic = "tele/" + path[1] + "/LWT"

        mqtt_availability_config = config
        mqtt_availability_config.update({
            CONF_AVAILABILITY_TOPIC: availability_topic,
            "payload_available": "Online",
            "payload_not_available": "Offline",
        })
        MqttAvailability.__init__(self, mqtt_availability_config)

    async def async_added_to_hass(self):
        """Run when entity about to be added."""
        await super().async_added_to_hass()

        # Add listener
        await self._subscribe_topics()

        # Check If we have an old state
        old_state = await self.async_get_last_state()
        if old_state is not None:
            # If we have no initial temperature, restore
            if old_state.attributes.get(ATTR_TEMPERATURE) is not None:
                self._target_temp = float(
                    old_state.attributes[ATTR_TEMPERATURE])
            if old_state.attributes.get(ATTR_PRESET_MODE) == PRESET_AWAY:
                self._is_away = True
            if old_state.attributes.get(ATTR_FAN_MODE) is not None:
                self._fan_mode = old_state.attributes.get(ATTR_FAN_MODE)
            if old_state.attributes.get(ATTR_SWING_MODE) is not None:
                self._swing_mode = old_state.attributes.get(ATTR_SWING_MODE)
            if old_state.attributes.get(ATTR_LAST_ON_MODE) is not None:
                self._last_on_mode = old_state.attributes.get(ATTR_LAST_ON_MODE)

            for attr, prop in ATTRIBUTES_IRHVAC.items():
                val = old_state.attributes.get(attr)
                if val is not None:
                    setattr(self, "_" + prop, val)
            if old_state.state:
                self._hvac_mode = old_state.state
                self._enabled = self._hvac_mode != HVAC_MODE_OFF
                if self._enabled:
                    self._last_on_mode = self._hvac_mode
            if self._swingv != "auto":
                self._fix_swingv = self._swingv
            if self._swingh != "auto":
                self._fix_swingh = self._swingh
        else:
            # No previous state, try and restore defaults
            if self._target_temp is None:
                self._target_temp = self._def_target_temp
            _LOGGER.warning(
                "No previously saved temperature, setting to %s", self._target_temp
            )

        if self._hvac_mode is HVAC_MODE_OFF:
            self.power_mode = STATE_OFF
            self._enabled = False
        else:
            self.power_mode = STATE_ON
            self._enabled = True

        for key in self._toggle_list:
            setattr(self, '_' + key.lower(), 'off')

        if self._temp_sensor:
            async_track_state_change(self.hass, self._temp_sensor, self._async_sensor_changed)

            temp_sensor_state = self.hass.states.get(self._temp_sensor)
            if temp_sensor_state and temp_sensor_state.state != STATE_UNKNOWN and temp_sensor_state.state != STATE_UNAVAILABLE:
                self._async_update_temp(temp_sensor_state)


        if self._humidity_sensor:
            async_track_state_change(self.hass, self._humidity_sensor, self._async_humidity_sensor_changed)

            humidity_sensor_state = self.hass.states.get(self._humidity_sensor)
            if humidity_sensor_state and humidity_sensor_state.state != STATE_UNKNOWN and humidity_sensor_state.state != STATE_UNAVAILABLE:
                self._async_update_humidity(humidity_sensor_state)

        if self._power_sensor:
            async_track_state_change(self.hass, self._power_sensor, self._async_power_sensor_changed)

    async def _subscribe_topics(self):
        """(Re)Subscribe to topics."""

        @callback
        async def state_message_received(msg):
            """Handle new MQTT state messages."""
            json_payload = json.loads(msg.payload)
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
                    self._hvac_mode = payload["Mode"].lower()
                    # Some vendors send/receive mode as fan instead of fan_only
                    if self._hvac_mode == CURRENT_HVAC_FAN:
                        self._hvac_mode = HVAC_MODE_FAN_ONLY
                if "Temp" in payload:
                    if payload["Temp"] > 0:
                        self._target_temp = payload["Temp"]
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
                if  "SwingV" in payload:
                    self._swingv = payload["SwingV"].lower()
                    if self._swingv != "auto":
                        self._fix_swingv = self._swingv
                if  "SwingH" in payload:
                    self._swingh = payload["SwingH"].lower()
                    if self._swingh != "auto":
                        self._fix_swingh = self._swingh
                if (
                    "SwingV" in payload
                    and payload["SwingV"].lower() == STATE_AUTO
                    and "SwingH" in payload
                    and payload["SwingH"].lower() == STATE_AUTO
                ):
                    if SWING_BOTH in self._swing_list:
                        self._swing_mode = SWING_BOTH
                    elif SWING_VERTICAL in self._swing_list:
                        self._swing_mode = SWING_VERTICAL
                    elif SWING_HORIZONTAL in self._swing_list:
                        self._swing_mode = SWING_HORIZONTAL
                    else:
                        self._swing_mode = SWING_OFF
                elif (
                    "SwingV" in payload
                    and payload["SwingV"].lower() == STATE_AUTO
                    and SWING_VERTICAL in self._swing_list
                ):
                    self._swing_mode = SWING_VERTICAL
                elif (
                    "SwingH" in payload
                    and payload["SwingH"].lower() == STATE_AUTO
                    and SWING_HORIZONTAL in self._swing_list
                ):
                    self._swing_mode = SWING_HORIZONTAL
                else:
                    self._swing_mode = SWING_OFF

                if "FanSpeed" in payload:
                    fan_mode = payload["FanSpeed"].lower()
                    # ELECTRA_AC fan modes fix
                    if (
                        HVAC_FAN_MAX_HIGH in self._fan_list
                        and HVAC_FAN_AUTO_MAX in self._fan_list
                    ):
                        if fan_mode == HVAC_FAN_MAX:
                            self._fan_mode = FAN_HIGH
                        elif fan_mode == HVAC_FAN_AUTO:
                            self._fan_mode = HVAC_FAN_MAX
                        else:
                            self._fan_mode = fan_mode
                    else:
                        self._fan_mode = fan_mode
                    _LOGGER.debug(self._fan_mode)

                if self._hvac_mode is not HVAC_MODE_OFF:
                    self._last_on_mode = self._hvac_mode

                # Set default state to off
                if self.power_mode == STATE_OFF:
                    self._hvac_mode = HVAC_MODE_OFF
                    self._enabled = False
                else:
                    self._enabled = True

                # Set toggles to 'off'
                for key in self._toggle_list:
                    setattr(self, '_' + key.lower(), 'off')

                # Update HA UI and State
                await self.async_update_ha_state()
                #self.async_schedule_update_ha_state()

                # Check power sensor state
                if self._power_sensor and prev_power is not None and prev_power != self.power_mode:
                    await asyncio.sleep(3)
                    state = self.hass.states.get(self._power_sensor)
                    await self._async_power_sensor_changed(self._power_sensor, None, state)

        topics = {
                    CONF_STATE_TOPIC: {
                        "topic": self.state_topic,
                        "msg_callback": state_message_received,
                        "qos": 1,
                    }
                }

        if hasattr(mqtt.subscription, 'async_prepare_subscribe_topics'):
            # for HA Core >= 2022.3.0
            self._sub_state = mqtt.subscription.async_prepare_subscribe_topics(
                self.hass,
                self._sub_state,
                topics,
            )

            await mqtt.subscription.async_subscribe_topics(self.hass, self._sub_state)

        else:
            # for HA Core < 2022.3.0
            self._sub_state = await mqtt.subscription.async_subscribe_topics(
                self.hass,
                self._sub_state,
                topics,
            )

    async def async_will_remove_from_hass(self):
        """Unsubscribe when removed."""
        self._sub_state = await mqtt.subscription.async_unsubscribe_topics(
            self.hass, self._sub_state
        )
        await MqttAvailability.async_will_remove_from_hass(self)

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the device."""
        return {attr: getattr(self, '_' + prop)
             for attr, prop in ATTRIBUTES_IRHVAC.items()}

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def name(self):
        """Return the name of the thermostat."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def precision(self):
        """Return the precision of the system."""
        if self._temp_precision is not None:
            return self._temp_precision
        return super().precision

    @property
    def target_temperature_step(self):
        """Return the supported step of target temperature."""
        return self._temp_step

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def current_temperature(self):
        """Return the sensor temperature."""
        return self._cur_temp

    @property
    def current_humidity(self):
        """Return the current humidity."""
        return self._cur_humidity

    @property
    def hvac_mode(self):
        """Return current operation."""
        return HVAC_MODE_OFF if self._hvac_mode in [STATE_UNKNOWN, STATE_UNAVAILABLE] else self._hvac_mode

    @property
    def hvac_action(self):
        """Return the current running hvac operation if supported.

        Need to be one of CURRENT_HVAC_*.
        """
        if self._hvac_mode == HVAC_MODE_OFF:
            return CURRENT_HVAC_OFF
        elif self._hvac_mode == HVAC_MODE_HEAT:
            return CURRENT_HVAC_HEAT
        elif self._hvac_mode == HVAC_MODE_COOL:
            return CURRENT_HVAC_COOL
        elif self._hvac_mode == HVAC_MODE_DRY:
            return CURRENT_HVAC_DRY
        elif self._hvac_mode == HVAC_MODE_FAN_ONLY:
            return CURRENT_HVAC_FAN

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temp

    @property
    def hvac_modes(self):
        """List of available operation modes."""
        return self._hvac_list

    @property
    def preset_mode(self):
        """Return the current preset mode, e.g., home, away, temp."""
        return PRESET_AWAY if self._is_away else PRESET_NONE

    @property
    def preset_modes(self):
        """Return a list of available preset modes or PRESET_NONE if _away_temp is undefined."""
        return [PRESET_NONE, PRESET_AWAY] if self._away_temp else PRESET_NONE

    @property
    def fan_mode(self):
        """Return the list of available fan modes.

        Requires SUPPORT_FAN_MODE.
        """
        return self._fan_mode

    @property
    def fan_modes(self):
        """Return the list of available fan modes.

        Requires SUPPORT_FAN_MODE.
        """
        # tweak for some ELECTRA_AC devices
        if HVAC_FAN_MAX_HIGH in self._fan_list and HVAC_FAN_AUTO_MAX in self._fan_list:
            new_fan_list = []
            for val in self._fan_list:
                if val == HVAC_FAN_MAX_HIGH:
                    new_fan_list.append(FAN_HIGH)
                elif val == HVAC_FAN_AUTO_MAX:
                    new_fan_list.append(HVAC_FAN_MAX)
                else:
                    new_fan_list.append(val)
            return new_fan_list
        return self._fan_list

    @property
    def swing_mode(self):
        """Return the swing setting.

        Requires SUPPORT_SWING_MODE.
        """
        return self._swing_mode

    @property
    def swing_modes(self):
        """Return the list of available swing modes.

        Requires SUPPORT_SWING_MODE.
        """
        return self._swing_list

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
        self._hvac_mode = self._last_on_mode if self._last_on_mode is not None else STATE_ON
        self.power_mode = STATE_ON
        await self.async_send_cmd()

    async def async_turn_off(self):
        """Turn thermostat off."""
        self._hvac_mode = HVAC_MODE_OFF
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

        self._target_temp = temperature
        if not self._hvac_mode == HVAC_MODE_OFF:
            self.power_mode = STATE_ON
        await self.async_send_cmd()

    async def async_set_fan_mode(self, fan_mode):
        """Set new target fan mode."""
        if fan_mode not in self._fan_list:
            #tweak for some ELECTRA_AC devices
            if HVAC_FAN_MAX_HIGH in self._fan_list and HVAC_FAN_AUTO_MAX in self._fan_list:
                if fan_mode != FAN_HIGH and fan_mode != HVAC_FAN_MAX:
                    _LOGGER.error(
                        "Invalid swing mode selected. Got '%s'. Allowed modes are:", fan_mode
                    )
                    _LOGGER.error(self._fan_list)
                    return
            else:
                _LOGGER.error(
                    "Invalid swing mode selected. Got '%s'. Allowed modes are:", fan_mode
                )
                _LOGGER.error(self._fan_list)
                return
        self._fan_mode = fan_mode
        if not self._hvac_mode == HVAC_MODE_OFF:
            self.power_mode = STATE_ON
        await self.async_send_cmd()

    async def async_set_swing_mode(self, swing_mode):
        """Set new target swing operation."""
        if swing_mode not in self._swing_list:
            _LOGGER.error(
                "Invalid swing mode selected. Got '%s'. Allowed modes are:", swing_mode
            )
            _LOGGER.error(self._swing_list)
            return
        self._swing_mode = swing_mode
        # note: set _swingv and _swingh in send_ir() later
        if not self._hvac_mode == HVAC_MODE_OFF:
            self.power_mode = STATE_ON
        await self.async_send_cmd()

    async def async_set_econo(self, econo):
        """Set new target econo mode."""
        if econo not in ON_OFF_LIST:
            return
        self._econo = econo.lower()
        await self.async_send_cmd()

    async def async_set_turbo(self, turbo):
        """Set new target turbo mode."""
        if turbo not in ON_OFF_LIST:
            return
        self._turbo = turbo.lower()
        await self.async_send_cmd()

    async def async_set_quiet(self, quiet):
        """Set new target quiet mode."""
        if quiet not in ON_OFF_LIST:
            return
        self._quiet = quiet.lower()
        await self.async_send_cmd()

    async def async_set_light(self, light):
        """Set new target light mode."""
        if light not in ON_OFF_LIST:
            return
        self._light = light.lower()
        await self.async_send_cmd()

    async def async_set_filters(self, filters):
        """Set new target filters mode."""
        if filters not in ON_OFF_LIST:
            return
        self._filter = filters.lower()
        await self.async_send_cmd()

    async def async_set_clean(self, clean):
        """Set new target clean mode."""
        if clean not in ON_OFF_LIST:
            return
        self._clean = clean.lower()
        await self.async_send_cmd()

    async def async_set_beep(self, beep):
        """Set new target beep mode."""
        if beep not in ON_OFF_LIST:
            return
        self._beep = beep.lower()
        await self.async_send_cmd()

    async def async_set_sleep(self, sleep):
        """Set new target sleep mode."""
        self._sleep = sleep.lower()
        await self.async_send_cmd()

    async def async_set_swingv(self, swingv):
        """Set new target swingv."""
        self._swingv = swingv.lower()
        if self._swingv != "auto":
            self._fix_swingv = self._swingv
            if self._swing_mode == SWING_BOTH:
                if SWING_HORIZONTAL in self._swing_list:
                    self._swing_mode = SWING_HORIZONTAL
            elif self._swing_mode == SWING_VERTICAL:
                self._swing_mode = SWING_OFF
        else:
            if self._swing_mode == SWING_HORIZONTAL:
                if SWING_BOTH in self._swing_list:
                    self._swing_mode = SWING_BOTH
            else:
                if SWING_VERTICAL in self._swing_list:
                    self._swing_mode = SWING_VERTICAL
        await self.async_send_cmd()

    async def async_set_swingh(self, swingh):
        """Set new target swingh."""
        self._swingh = swingh.lower()
        if self._swingh != "auto":
            self._fix_swingh = self._swingh
            if self._swing_mode == SWING_BOTH:
                if SWING_VERTICAL in self._swing_list:
                    self._swing_mode = SWING_VERTICAL
            elif self._swing_mode == SWING_HORIZONTAL:
                self._swing_mode = SWING_OFF
        else:
            if self._swing_mode == SWING_VERTICAL:
                if SWING_BOTH in self._swing_list:
                    self._swing_mode = SWING_BOTH
            else:
                if SWING_HORIZONTAL in self._swing_list:
                    self._swing_mode = SWING_HORIZONTAL
        await self.async_send_cmd()

    async def _async_power_sensor_changed(self, entity_id, old_state, new_state):
        """Handle power sensor changes."""
        if new_state is None:
            return

        if old_state is not None and new_state.state == old_state.state:
            return

        if new_state.state == STATE_ON:
            if self._hvac_mode == HVAC_MODE_OFF or self.power_mode == STATE_OFF:
                if self._last_on_mode is not None:
                    self._hvac_mode = self._last_on_mode
                else:
                    self._hvac_mode = STATE_ON
                self.power_mode = STATE_ON
                await self.async_update_ha_state()

        elif new_state.state == STATE_OFF:
            if self._hvac_mode != HVAC_MODE_OFF or self.power_mode == STATE_ON:
                self._hvac_mode = HVAC_MODE_OFF
                self.power_mode = STATE_OFF
                await self.async_update_ha_state()

    async def async_send_cmd(self):
        await self.send_ir()
        await self.async_update_ha_state()

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        if self._min_temp:
            return self._min_temp

        # get default temp from super class
        return super().min_temp

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        if self._max_temp:
            return self._max_temp

        # Get default temp from super class
        return super().max_temp

    async def _async_sensor_changed(self, entity_id, old_state, new_state):
        """Handle temperature changes."""
        if new_state is None:
            return

        self._async_update_temp(new_state)
        await self.async_update_ha_state()

    async def _async_humidity_sensor_changed(self, entity_id, old_state, new_state):
        """Handle humidity sensor changes."""
        if new_state is None:
            return

        self._async_update_humidity(new_state)
        await self.async_update_ha_state()

    @callback
    def _async_update_temp(self, state):
        """Update thermostat with latest state from sensor."""
        try:
            self._cur_temp = float(state.state)
        except ValueError as ex:
            _LOGGER.debug("Unable to update from sensor: %s", ex)

    @callback
    def _async_update_humidity(self, state):
        """Update thermostat with latest state from humidity sensor."""
        try:
            if state.state != STATE_UNKNOWN and state.state != STATE_UNAVAILABLE:
                self._cur_humidity = float(state.state)
        except ValueError as ex:
            _LOGGER.error("Unable to update from humidity sensor: %s", ex)

    @property
    def _is_device_active(self):
        """If the toggleable device is currently active."""
        return self.power_mode == STATE_ON

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return self._support_flags

    async def async_set_preset_mode(self, preset_mode):
        """Set new preset mode.

        This method must be run in the event loop and returns a coroutine.
        """
        if preset_mode == PRESET_AWAY and not self._is_away:
            self._is_away = True
            self._saved_target_temp = self._target_temp
            self._target_temp = self._away_temp
        elif preset_mode == PRESET_NONE and self._is_away:
            self._is_away = False
            self._target_temp = self._saved_target_temp
        await self.send_ir()
        await self.async_update_ha_state()

    async def set_mode(self, hvac_mode):
        """Set hvac mode."""
        hvac_mode = hvac_mode.lower()
        if hvac_mode not in self._hvac_list or hvac_mode == HVAC_MODE_OFF:
            self._hvac_mode = HVAC_MODE_OFF
            self._enabled = False
            self.power_mode = STATE_OFF
        else:
            self._hvac_mode = self._last_on_mode = hvac_mode
            self._enabled = True
            self.power_mode = STATE_ON

    async def send_ir(self):
        """Send the payload to tasmota mqtt topic."""
        fan_speed = self.fan_mode
        # tweak for some ELECTRA_AC devices
        if HVAC_FAN_MAX_HIGH in self._fan_list and HVAC_FAN_AUTO_MAX in self._fan_list:
            if self.fan_mode == FAN_HIGH:
                fan_speed = HVAC_FAN_MAX
            if self.fan_mode == HVAC_FAN_MAX:
                fan_speed = HVAC_FAN_AUTO


        # Set the swing mode - default off
        self._swingv = STATE_OFF if self._fix_swingv is None else self._fix_swingv
        self._swingh = STATE_OFF if self._fix_swingh is None else self._fix_swingh

        if SWING_BOTH in self._swing_list or SWING_VERTICAL in self._swing_list:
            if self._swing_mode == SWING_BOTH or self._swing_mode == SWING_VERTICAL:
                self._swingv = STATE_AUTO

        if SWING_BOTH in self._swing_list or SWING_HORIZONTAL in self._swing_list:
            if self._swing_mode == SWING_BOTH or self._swing_mode == SWING_HORIZONTAL:
                self._swingh = STATE_AUTO

        _dt = dt_util.now()
        _min = _dt.hour * 60 + _dt.minute

        # Populate the payload
        payload_data = {
            "StateMode": "SendStore",
            "Vendor": self._vendor,
            "Model": self._model,
            "Power": self.power_mode,
            "Mode": self._last_on_mode if self._keep_mode else self._hvac_mode,
            "Celsius": self._celsius,
            "Temp": self._target_temp,
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
        for key in self._toggle_list:
            setattr(self, '_' + key.lower(), 'off')

        payload = (json.dumps(payload_data))
        # Publish mqtt message
        await mqtt.async_publish(self.hass, self.topic, payload)

        # Update HA UI and State
        self.async_schedule_update_ha_state()
