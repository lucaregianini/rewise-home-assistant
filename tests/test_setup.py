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


async def test_reload_removes_deleted_entities(hass, code, status, payload):
    from homeassistant.helpers import entity_registry as er

    from custom_components.rewise.code import encode_code

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
        registry = er.async_get(hass)
        kept = registry.async_get_entity_id(
            "button", "rewise", "A2-TEST01_btn_power-test"
        )
        registry.async_update_entity(kept, name="My power button")
        payload["devices"][0]["buttons"] = payload["devices"][0]["buttons"][:1]
        payload.pop("otherACs")
        status["extras"] = {"stateful": False, "supported": ["light"]}
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, "code": encode_code(payload)}
        )
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert (
            registry.async_get_entity_id("button", "rewise", "A2-TEST01_btn_raw-test")
            is None
        )
        assert (
            registry.async_get_entity_id("climate", "rewise", "A2-TEST01_other_ac-test")
            is None
        )
        assert (
            registry.async_get_entity_id("switch", "rewise", "A2-TEST01_extra_swingV")
            is None
        )
        assert (
            registry.async_get_entity_id("button", "rewise", "A2-TEST01_extra_light")
            is not None
        )
        assert registry.async_get(kept).name == "My power button"
        assert await hass.config_entries.async_unload(entry.entry_id)


async def test_only_extras_from_the_app_page(hass, code, status, payload):
    """Coolix lists five extras; Home Assistant shows only those the owner uses."""
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    from custom_components.rewise.code import encode_code

    status["extras"] = {
        "stateful": False,
        "supported": ["swingV", "turbo", "light", "sleep", "clean"],
    }
    payload["extras"] = ["turbo", "light"]
    entry = MockConfigEntry(
        domain="rewise",
        unique_id="A2-TEST01",
        title="Living Room",
        data={"host": "192.0.2.1", "code": encode_code(payload)},
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
        registry = er.async_get(hass)

        def extras():
            return sorted(
                e.unique_id.rsplit("_", 1)[-1]
                for e in er.async_entries_for_config_entry(registry, entry.entry_id)
                if "_extra_" in e.unique_id
            )

        assert extras() == ["light", "turbo"]
        (device,) = dr.async_entries_for_config_entry(
            dr.async_get(hass), entry.entry_id
        )
        assert device.serial_number == "A2-TEST01"
        # The owner adds Swing in the app and pastes a fresh code (Reconfigure).
        payload["extras"] = ["turbo", "light", "swingV"]
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, "code": encode_code(payload)}
        )
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert extras() == ["light", "swingV", "turbo"]
        assert await hass.config_entries.async_unload(entry.entry_id)
