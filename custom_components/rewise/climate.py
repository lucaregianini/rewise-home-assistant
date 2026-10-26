"""Main and additional air conditioners controlled by Rewise Air."""

from __future__ import annotations

import asyncio
import math
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate.const import ATTR_HVAC_MODE
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import RewiseConfigEntry
from .code import OtherAC
from .const import FAN_MODES, MAX_TEMP, MIN_TEMP
from .coordinator import RewiseCoordinator
from .entity import RewiseEntity

MODE_TO_HVAC = {
    "auto": HVACMode.AUTO,
    "cool": HVACMode.COOL,
    "heat": HVACMode.HEAT,
    "dry": HVACMode.DRY,
    "fanOnly": HVACMode.FAN_ONLY,
}
HVAC_TO_MODE = {v: k for k, v in MODE_TO_HVAC.items()}


def temperature(value: float) -> int:
    """Reject invalid temperatures before sending an IR command."""
    if not math.isfinite(value) or not MIN_TEMP <= value <= MAX_TEMP:
        raise ValueError("Temperature must be between 17 and 30")
    return round(value)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RewiseConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            RewiseAirClimate(coordinator),
            *(RewiseOtherClimate(coordinator, ac) for ac in coordinator.code.other_acs),
        ]
    )


class RewiseAirClimate(RewiseEntity, ClimateEntity):
    """State reported by the Air A2 for its main air conditioner."""

    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 1
    _attr_min_temp = MIN_TEMP
    _attr_max_temp = MAX_TEMP
    _attr_hvac_modes = [HVACMode.OFF, *MODE_TO_HVAC.values()]
    _attr_fan_modes = FAN_MODES
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_extra_state_attributes = {
        "ir_state_note": "IR is one-way. State is what Rewise Air last sent or heard from the remote."
    }

    def __init__(self, coordinator: RewiseCoordinator) -> None:
        super().__init__(coordinator, "ac")

    @property
    def _ac(self) -> dict[str, Any]:
        return self.coordinator.data["ac"]

    @property
    def hvac_mode(self) -> HVACMode:
        return (
            MODE_TO_HVAC.get(self._ac["mode"], HVACMode.AUTO)
            if self._ac["power"]
            else HVACMode.OFF
        )

    @property
    def target_temperature(self) -> int:
        return self._ac["temperatureC"]

    @property
    def fan_mode(self) -> str:
        return self._ac["fan"]

    @property
    def current_temperature(self) -> float | None:
        return self.coordinator.data["environment"].get("temperatureC")

    @property
    def current_humidity(self) -> float | None:
        return self.coordinator.data["environment"].get("relativeHumidity")

    async def _send(self, **fields: Any) -> None:
        await self.coordinator.command(
            lambda: self.coordinator.client.control(**fields)
        )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self._send(
            **(
                {"power": False}
                if hvac_mode == HVACMode.OFF
                else {"power": True, "mode": HVAC_TO_MODE[hvac_mode]}
            )
        )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        fields: dict[str, Any] = {}
        if ATTR_TEMPERATURE in kwargs:
            fields["temperatureC"] = temperature(kwargs[ATTR_TEMPERATURE])
        if (mode := kwargs.get(ATTR_HVAC_MODE)) is not None:
            fields["power"] = mode != HVACMode.OFF
            if mode != HVACMode.OFF:
                fields["mode"] = HVAC_TO_MODE[mode]
        await self._send(**fields)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        await self._send(fan=fan_mode)

    async def async_turn_on(self) -> None:
        await self._send(power=True)

    async def async_turn_off(self) -> None:
        await self._send(power=False)


class RewiseOtherClimate(RewiseAirClimate, RestoreEntity):
    """The second AC has assumed state because the Air A2 does not retain it."""

    _attr_assumed_state = True

    def __init__(self, coordinator: RewiseCoordinator, ac: OtherAC) -> None:
        super().__init__(coordinator)
        self.other = ac
        self._attr_unique_id = f"{coordinator.code.device_id}_other_{ac.key}"
        self._attr_name = ac.name
        self.state_lock = asyncio.Lock()
        self.local = {"power": False, "mode": "cool", "fan": "auto", "temperatureC": 24}

    @property
    def _ac(self) -> dict[str, Any]:
        return self.local

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (state := await self.async_get_last_state()) is not None:
            try:
                mode = HVACMode(state.state)
                fan = state.attributes.get("fan_mode", "auto")
                self.local = {
                    "power": mode != HVACMode.OFF,
                    "mode": HVAC_TO_MODE.get(mode, "cool"),
                    "fan": fan if fan in FAN_MODES else "auto",
                    "temperatureC": temperature(
                        float(state.attributes.get("temperature", 24))
                    ),
                }
            except (TypeError, ValueError):
                pass

    async def _send(self, **fields: Any) -> None:
        async with self.state_lock:
            desired = self.local | fields
            await self.coordinator.command(
                lambda: self.coordinator.client.other_ac(
                    self.other.protocol,
                    self.other.model,
                    desired["power"],
                    desired["mode"],
                    desired["fan"],
                    desired["temperatureC"],
                ),
                updates_status=False,
            )
            self.local = desired
            self.async_write_ha_state()
