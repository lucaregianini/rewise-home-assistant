from __future__ import annotations
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from . import RewiseConfigEntry
async def async_setup_entry(hass: HomeAssistant, entry: RewiseConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up entities."""
