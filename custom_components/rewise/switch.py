"""Stateful AC extras."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RewiseConfigEntry
from .const import EXTRA_NAMES
from .coordinator import RewiseCoordinator
from .entity import RewiseEntity


def extra_key(name: str) -> str:
    """Translate firmware names to HA translation keys."""
    return {"swingV": "swing_v", "swingH": "swing_h"}.get(name, name)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RewiseConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    if coordinator.data["extras"].get("stateful"):
        async_add_entities(
            [
                RewiseExtraSwitch(coordinator, name)
                for name in coordinator.data["extras"].get("supported", [])
            ]
        )


class RewiseExtraSwitch(RewiseEntity, SwitchEntity):
    """An extra whose state is retained by the Air A2."""

    def __init__(self, coordinator: RewiseCoordinator, name: str) -> None:
        super().__init__(coordinator, f"extra_{name}")
        self.extra = name
        if name in EXTRA_NAMES:
            self._attr_translation_key = extra_key(name)
        else:
            self._attr_name = name

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.data["extras"].get("state", {}).get(self.extra)

    async def async_turn_on(self, **kwargs: object) -> None:
        await self.coordinator.command(
            lambda: self.coordinator.client.extra(self.extra, True)
        )

    async def async_turn_off(self, **kwargs: object) -> None:
        await self.coordinator.command(
            lambda: self.coordinator.client.extra(self.extra, False)
        )
