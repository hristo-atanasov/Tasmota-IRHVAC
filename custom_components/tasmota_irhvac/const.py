"""Provides the constants needed for component."""

# States
STATE_AUTO = "auto"
STATE_COOL = "cool"
STATE_DRY = "dry"
STATE_FAN_ONLY = "fan_only"
STATE_HEAT = "heat"

# Fan speeds
HVAC_FAN_AUTO = "auto"
HVAC_FAN_MIN = "min"
HVAC_FAN_MEDIUM = "medium"
HVAC_FAN_MAX = "max"

# Some devices have "auto" and "fan_only" changed
HVAC_MODE_AUTO_FAN = "auto_fan_only"

# Some devicec have "fan_only" and "auto" changed
HVAC_MODE_FAN_AUTO = "fan_only_auto"

# Some devices say max,but it is high, and auto which is max
HVAC_FAN_MAX_HIGH = "max_high"
HVAC_FAN_AUTO_MAX = "auto_max"

# All activity disabled / Device is off/standby
HVAC_MODE_OFF = "off"

# Heating
HVAC_MODE_HEAT = "heat"

# Cooling
HVAC_MODE_COOL = "cool"

# The device supports heating/cooling to a range
HVAC_MODE_HEAT_COOL = "heat_cool"

# The temperature is set based on a schedule, learned behavior, AI or some
# other related mechanism. User is not able to adjust the temperature
HVAC_MODE_AUTO = "auto"

# Device is in Dry/Humidity mode
HVAC_MODE_DRY = "dry"

# Only the fan is on, not fan and another mode like cool
HVAC_MODE_FAN_ONLY = "fan_only"

# Hvac moed list
HVAC_MODES = [
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_HEAT_COOL,
    HVAC_MODE_AUTO,
    HVAC_MODE_DRY,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_AUTO_FAN,
    HVAC_MODE_FAN_AUTO,
]

# Platform specific config entry names
CONF_EXCLUSIVE_GROUP_VENDOR = "exclusive_group_vendor"
CONF_VENDOR = "vendor"
CONF_PROTOCOL = "protocol"  # Soon to be deprecated
CONF_COMMAND_TOPIC = "command_topic"
CONF_STATE_TOPIC = "state_topic"
CONF_TEMP_SENSOR = "temperature_sensor"
CONF_HUMIDITY_SENSOR = "humidity_sensor"
CONF_POWER_SENSOR = "power_sensor"
CONF_MIN_TEMP = "min_temp"
CONF_MAX_TEMP = "max_temp"
CONF_TARGET_TEMP = "target_temp"
CONF_INITIAL_OPERATION_MODE = "initial_operation_mode"
CONF_AWAY_TEMP = "away_temp"
CONF_PRECISION = "precision"
CONF_TEMP_STEP = "temp_step"
CONF_MODES_LIST = "supported_modes"
CONF_FAN_LIST = "supported_fan_speeds"
CONF_SWING_LIST = "supported_swing_list"
CONF_QUIET = "default_quiet_mode"
CONF_TURBO = "default_turbo_mode"
CONF_ECONO = "default_econo_mode"
CONF_MODEL = "hvac_model"
CONF_CELSIUS = "celsius_mode"
CONF_LIGHT = "default_light_mode"
CONF_FILTER = "default_filter_mode"
CONF_CLEAN = "default_clean_mode"
CONF_BEEP = "default_beep_mode"
CONF_SLEEP = "default_sleep_mode"
CONF_KEEP_MODE = "keep_mode_when_off"
CONF_SWINGV = "default_swingv"
CONF_SWINGH = "default_swingh"
CONF_TOGGLE_LIST = "toggle_list"

# Platform specific default values
DEFAULT_NAME = "IR AirConditioner"
DEFAULT_STATE_TOPIC = "state"
DEFAULT_COMMAND_TOPIC = "topic"
DEFAULT_TARGET_TEMP = 26
DEFAULT_MIN_TEMP = 16
DEFAULT_MAX_TEMP = 32
DEFAULT_PRECISION = 1
DEFAULT_FAN_LIST = [HVAC_FAN_AUTO_MAX,
                    HVAC_FAN_MAX_HIGH, HVAC_FAN_MEDIUM, HVAC_FAN_MIN]
DEFAULT_CONF_QUIET = "off"
DEFAULT_CONF_TURBO = "off"
DEFAULT_CONF_ECONO = "off"
DEFAULT_CONF_MODEL = "-1"
DEFAULT_CONF_CELSIUS = "on"
DEFAULT_CONF_LIGHT = "off"
DEFAULT_CONF_FILTER = "off"
DEFAULT_CONF_CLEAN = "off"
DEFAULT_CONF_BEEP = "off"
DEFAULT_CONF_SLEEP = "-1"
DEFAULT_CONF_KEEP_MODE = False

ATTR_NAME = "name"
ATTR_VALUE = "value"

DATA_KEY = 'tasmota_irhvac.climate'
DOMAIN = 'tasmota_irhvac'

ATTR_ECONO = 'econo'
ATTR_TURBO = 'turbo'
ATTR_QUIET = 'quiet'
ATTR_LIGHT = 'light'
ATTR_FILTERS = 'filters'
ATTR_CLEAN = 'clean'
ATTR_BEEP = 'beep'
ATTR_SLEEP = 'sleep'
ATTR_LAST_ON_MODE = 'last_on_mode'
ATTR_SWINGV = 'swingv'
ATTR_SWINGH = 'swingh'
ATTR_FIX_SWINGV = 'fix_swingv'
ATTR_FIX_SWINGH = 'fix_swingh'

SERVICE_ECONO_MODE = 'set_econo'
SERVICE_TURBO_MODE = 'set_turbo'
SERVICE_QUIET_MODE = 'set_quiet'
SERVICE_LIGHT_MODE = 'set_light'
SERVICE_FILTERS_MODE = 'set_filters'
SERVICE_CLEAN_MODE = 'set_clean'
SERVICE_BEEP_MODE = 'set_beep'
SERVICE_SLEEP_MODE = 'set_sleep'
SERVICE_SET_SWINGV = 'set_swingv'
SERVICE_SET_SWINGH = 'set_swingh'

# Map attributes to properties of the state object
ATTRIBUTES_IRHVAC = {
    ATTR_ECONO: 'econo',
    ATTR_TURBO: 'turbo',
    ATTR_QUIET: 'quiet',
    ATTR_LIGHT: 'light',
    ATTR_FILTERS: 'filter',
    ATTR_CLEAN: 'clean',
    ATTR_BEEP: 'beep',
    ATTR_SLEEP: 'sleep',
    ATTR_LAST_ON_MODE: 'last_on_mode',
    ATTR_SWINGV: 'swingv',
    ATTR_SWINGH: 'swingh',
    ATTR_FIX_SWINGV: 'fix_swingv',
    ATTR_FIX_SWINGH: 'fix_swingh',
}

ON_OFF_LIST = [
    'ON',
    'OFF',
    'On',
    'Off',
    'on',
    'off'
]

TOGGLE_ALL_LIST = [
    'SwingV',
    'SwingH',
    'Quiet',
    'Turbo',
    'Econo',
    'Light',
    'Filter',
    'Clean',
    'Beep',
    'Sleep',
]
