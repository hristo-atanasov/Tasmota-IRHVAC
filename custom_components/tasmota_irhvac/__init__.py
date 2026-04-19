"""The Tasmota IRHVAC integration."""

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DATA_KEY, DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Tasmota IRHVAC integration."""
    hass.data.setdefault(DOMAIN, {})
    hass.data.setdefault(DATA_KEY, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tasmota IRHVAC from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data.setdefault(DATA_KEY, {})

    _register_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


def _register_services(hass: HomeAssistant) -> None:
    """Register IRHVAC services (idempotent)."""
    from .climate import SERVICE_TO_METHOD, IRHVAC_SERVICE_SCHEMA

    if hass.services.has_service(DOMAIN, "set_econo"):
        return

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
            update_tasks.append(
                asyncio.create_task(device.async_update_ha_state(True))
            )

        if update_tasks:
            await asyncio.wait(update_tasks)

    for irhvac_service, method_info in SERVICE_TO_METHOD.items():
        schema = method_info.get("schema", IRHVAC_SERVICE_SCHEMA)
        hass.services.async_register(
            DOMAIN, irhvac_service, async_service_handler, schema=schema
        )
