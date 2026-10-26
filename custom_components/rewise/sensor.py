"""Room measurements and optional diagnostics."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RewiseConfigEntry
from .coordinator import RewiseCoordinator
from .entity import RewiseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RewiseConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        [
            RewiseSensor(entry.runtime_data, key)
            for key in ("temperature", "humidity", "rssi", "firmware")
        ]
    )


class RewiseSensor(RewiseEntity, SensorEntity):
    """Read one value from the shared coordinator."""

    def __init__(self, coordinator: RewiseCoordinator, key: str) -> None:
        super().__init__(coordinator, key)
        self.key = key
        self._attr_translation_key = key
        if key in ("temperature", "humidity"):
            self._attr_device_class = (
                SensorDeviceClass.TEMPERATURE
                if key == "temperature"
                else SensorDeviceClass.HUMIDITY
            )
            self._attr_native_unit_of_measurement = (
                UnitOfTemperature.CELSIUS if key == "temperature" else "%"
            )
            self._attr_state_class = SensorStateClass.MEASUREMENT
        else:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_entity_registry_enabled_default = False
            if key == "rssi":
                self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
                self._attr_native_unit_of_measurement = (
                    SIGNAL_STRENGTH_DECIBELS_MILLIWATT
                )
                self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> str | float | None:
        if self.key == "rssi":
            return self.coordinator.sensor_data.get("rssi")
        if self.key == "firmware":
            return self.coordinator.data["device"].get("firmwareVersion")
        return self.coordinator.data["environment"].get(
            "temperatureC" if self.key == "temperature" else "relativeHumidity"
        )
