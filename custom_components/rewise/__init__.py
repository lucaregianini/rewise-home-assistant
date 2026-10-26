"""Rewise Air A2 local integration."""
from __future__ import annotations
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .api import RewiseAirClient
from .code import InvalidCode, decode_code
from .const import CONF_CODE
from .coordinator import RewiseCoordinator

PLATFORMS = [Platform.CLIMATE, Platform.SENSOR, Platform.SWITCH, Platform.BUTTON]
type RewiseConfigEntry = ConfigEntry[RewiseCoordinator]

async def async_setup_entry(hass: HomeAssistant, entry: RewiseConfigEntry) -> bool:
    """Set up one Air A2 from its connection code."""
    try:
        code = decode_code(entry.data[CONF_CODE])
    except InvalidCode as err:
        raise ConfigEntryError("Invalid Rewise connection code") from err
    client = RewiseAirClient(async_get_clientsession(hass), entry.data[CONF_HOST], code.user, code.password)
    coordinator = RewiseCoordinator(hass, entry, client, code)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: RewiseConfigEntry) -> bool:
    """Unload all entities belonging to the Air A2."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
