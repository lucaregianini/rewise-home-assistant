from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_setup_unload(hass, code, status):
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
        patch(
            "custom_components.rewise.api.RewiseAirClient.sensor",
            return_value={"rssi": -55},
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert hass.states.get("climate.living_room") is not None
        assert hass.states.get("sensor.living_room_temperature").state == "25.1"
        assert await hass.config_entries.async_unload(entry.entry_id)
