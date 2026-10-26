import pytest
from homeassistant.components.climate import HVACMode

from custom_components.rewise.climate import MODE_TO_HVAC, RewiseAirClimate


@pytest.mark.parametrize("mode", list(HVACMode))
async def test_modes(coordinator, mode):
    if mode == HVACMode.HEAT_COOL:
        return
    entity = RewiseAirClimate(coordinator)
    await entity.async_set_hvac_mode(mode)
    expected = (
        {"power": False}
        if mode == HVACMode.OFF
        else {
            "power": True,
            "mode": next(k for k, v in MODE_TO_HVAC.items() if v == mode),
        }
    )
    coordinator.client.control.assert_awaited_once_with(**expected)


async def test_temperature_fan_and_power(coordinator):
    entity = RewiseAirClimate(coordinator)
    assert entity.current_temperature == 25.1 and entity.current_humidity == 52
    assert entity.hvac_mode == HVACMode.COOL
    await entity.async_set_temperature(temperature=25, hvac_mode=HVACMode.HEAT)
    coordinator.client.control.assert_awaited_once_with(
        temperatureC=25, power=True, mode="heat"
    )
    for fan in ("auto", "low", "medium", "high"):
        await entity.async_set_fan_mode(fan)
        coordinator.client.control.assert_awaited_with(fan=fan)
    await entity.async_turn_off()
    coordinator.client.control.assert_awaited_with(power=False)
    await entity.async_turn_on()
    coordinator.client.control.assert_awaited_with(power=True)
    coordinator.data["environment"] = {"temperatureC": None, "relativeHumidity": None}
    assert entity.current_temperature is None and entity.current_humidity is None
    coordinator.data["ac"]["power"] = False
    assert entity.hvac_mode == HVACMode.OFF
