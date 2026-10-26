"""One-shot AC extras and learned remote buttons."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RewiseConfigEntry
from .code import LearnedButton
from .const import EXTRA_NAMES
from .coordinator import RewiseCoordinator
from .entity import RewiseEntity
from .switch import extra_key


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RewiseConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[ButtonEntity] = []
    if not coordinator.data["extras"].get("stateful"):
        entities.extend(
            RewiseExtraButton(coordinator, name) for name in coordinator.extras
        )
    for device in coordinator.code.devices:
        entities.extend(
            RewiseLearnedButton(coordinator, device.name, device.kind, button)
            for button in device.buttons
        )
    async_add_entities(entities)


class RewiseExtraButton(RewiseEntity, ButtonEntity):
    """Coolix extras are toggles, so never pretend to know their state."""

    def __init__(self, coordinator: RewiseCoordinator, name: str) -> None:
        super().__init__(coordinator, f"extra_{name}")
        self.extra = name
        if name in EXTRA_NAMES:
            self._attr_translation_key = extra_key(name)
        else:
            self._attr_name = name

    async def async_press(self) -> None:
        await self.coordinator.command(
            lambda: self.coordinator.client.extra(self.extra, True)
        )


KIND_ICONS = {
    "airConditioner": "mdi:air-conditioner",
    "tv": "mdi:television",
    "light": "mdi:lightbulb",
    "fan": "mdi:fan",
    "speaker": "mdi:speaker",
    "projector": "mdi:projector",
}


class RewiseLearnedButton(RewiseEntity, ButtonEntity):
    """Replay exactly the body exported by the Rewise app."""

    def __init__(
        self,
        coordinator: RewiseCoordinator,
        device_name: str,
        kind: str,
        button: LearnedButton,
    ) -> None:
        super().__init__(coordinator, f"btn_{button.key}")
        self.button = button
        self._attr_name = f"{device_name} {button.name}"
        self._attr_icon = KIND_ICONS.get(kind, "mdi:remote")

    async def async_press(self) -> None:
        await self.coordinator.command(
            lambda: self.coordinator.client.ir_send(self.button.ir),
            updates_status=False,
        )
