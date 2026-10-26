from unittest.mock import patch

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.rewise.api import ApiError, AuthFailed, CannotConnect
from custom_components.rewise.diagnostics import async_get_config_entry_diagnostics


async def test_poll_sensor_cadence(coordinator, status):
    coordinator.client.status.return_value = status
    coordinator.client.sensor.return_value = {"rssi": -55}
    with patch(
        "custom_components.rewise.coordinator.time.monotonic",
        side_effect=[100, 130, 400],
    ):
        await coordinator._async_update_data()
        await coordinator._async_update_data()
        await coordinator._async_update_data()
    assert coordinator.client.sensor.await_count == 2


async def test_profile_reload(coordinator, status):
    coordinator.client.status.return_value = status
    coordinator.client.sensor.return_value = {}
    await coordinator._async_update_data()
    status["extras"]["supported"] = ["light"]
    with patch.object(
        coordinator.hass.config_entries, "async_reload", return_value=True
    ) as reload:
        await coordinator._async_update_data()
        await coordinator.hass.async_block_till_done()
        reload.assert_awaited_once()


@pytest.mark.parametrize(
    "error,expected",
    [(AuthFailed(), ConfigEntryAuthFailed), (CannotConnect(), UpdateFailed)],
)
async def test_poll_errors(coordinator, error, expected):
    coordinator.client.status.side_effect = error
    with pytest.raises(expected):
        await coordinator._async_update_data()


@pytest.mark.parametrize(
    "error",
    [
        CannotConnect(),
        ApiError("busy", "Busy"),
        ApiError("other", "Failed"),
        AuthFailed(),
    ],
)
async def test_command_errors(coordinator, error):
    coordinator.client.control.side_effect = error
    with patch.object(coordinator.config_entry, "async_start_reauth"):
        with pytest.raises(HomeAssistantError):
            await coordinator.command(lambda: coordinator.client.control(power=True))


async def test_diagnostics(coordinator):
    coordinator.config_entry.runtime_data = coordinator
    data = await async_get_config_entry_diagnostics(
        coordinator.hass, coordinator.config_entry
    )
    assert data["connection"]["password"] == "**REDACTED**"
    assert data["connection"]["devices"][0]["buttons"][0]["ir"] == "**REDACTED**"
    assert "test-pass-123" not in str(data)
