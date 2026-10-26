from unittest.mock import patch

from homeassistant.components.climate import HVACMode
from homeassistant.core import State

from custom_components.rewise.climate import RewiseOtherClimate


async def test_full_state(coordinator):
    entity = RewiseOtherClimate(coordinator, coordinator.code.other_acs[0])
    with patch.object(entity, "async_write_ha_state"):
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        coordinator.client.other_ac.assert_awaited_with(
            "DAIKIN", -1, True, "heat", "auto", 24
        )
        await entity.async_set_temperature(temperature=26)
        coordinator.client.other_ac.assert_awaited_with(
            "DAIKIN", -1, True, "heat", "auto", 26
        )
        await entity.async_set_fan_mode("low")
        coordinator.client.other_ac.assert_awaited_with(
            "DAIKIN", -1, True, "heat", "low", 26
        )
        await entity.async_turn_off()
        coordinator.client.other_ac.assert_awaited_with(
            "DAIKIN", -1, False, "heat", "low", 26
        )
        assert entity.assumed_state is True


async def test_restore(hass, code, status):
    from pytest_homeassistant_custom_component.common import (
        MockConfigEntry,
        mock_restore_cache,
    )

    mock_restore_cache(
        hass,
        [
            State(
                "climate.living_room_window_ac",
                "heat",
                {"temperature": 27, "fan_mode": "high"},
            )
        ],
    )
    entry = MockConfigEntry(
        domain="rewise",
        unique_id="A2-TEST01",
        title="Living Room",
        data={"host": "192.0.2.1", "code": code},
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.rewise.api.RewiseAirClient.status", return_value=status
        ),
        patch("custom_components.rewise.api.RewiseAirClient.sensor", return_value={}),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        state = hass.states.get("climate.living_room_window_ac")
        assert state.state == "heat"
        assert state.attributes["temperature"] == 27
        assert state.attributes["fan_mode"] == "high"
        assert await hass.config_entries.async_unload(entry.entry_id)
