"""Common identity for entities from one Air A2."""
from __future__ import annotations
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
from .coordinator import RewiseCoordinator

class RewiseEntity(CoordinatorEntity[RewiseCoordinator]):
    """An entity on the Rewise Air device."""
    _attr_has_entity_name = True
    def __init__(self, coordinator: RewiseCoordinator, suffix: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.code.device_id}_{suffix}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, coordinator.code.device_id)},
            name=coordinator.code.name, manufacturer="Rewise", model="Rewise Air A2",
            sw_version=coordinator.data["device"].get("firmwareVersion"))
