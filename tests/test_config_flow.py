from unittest.mock import patch

import pytest
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rewise.api import AuthFailed, CannotConnect
from custom_components.rewise.code import encode_code


@pytest.fixture
def discovery():
    return ZeroconfServiceInfo(
        ip_address="192.0.2.1",
        ip_addresses=["192.0.2.1"],
        hostname="test.local.",
        name="test._smartachub._tcp.local.",
        port=80,
        type="_smartachub._tcp.local.",
        properties={"model": "Rewise Air A2", "id": "A2-TEST01"},
    )


async def test_manual(hass, code, status):
    with (
        patch(
            "custom_components.rewise.config_flow.RewiseAirClient.status",
            return_value=status,
        ),
        patch("custom_components.rewise.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            "rewise", context={"source": "user"}
        )
        assert result["type"] == FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"host": "192.0.2.1", "code": code}
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "Living Room"
        assert result["result"].unique_id == "A2-TEST01"
        await hass.async_block_till_done()


@pytest.mark.parametrize(
    "error,expected",
    [(AuthFailed(), "invalid_auth"), (CannotConnect(), "cannot_connect")],
)
async def test_errors(hass, code, error, expected):
    with patch(
        "custom_components.rewise.config_flow.RewiseAirClient.status", side_effect=error
    ):
        result = await hass.config_entries.flow.async_init(
            "rewise",
            context={"source": "user"},
            data={"host": "192.0.2.1", "code": code},
        )
        assert result["errors"] == {"base": expected}


async def test_discovery(hass, discovery, code, status, payload):
    result = await hass.config_entries.flow.async_init(
        "rewise", context={"source": "zeroconf"}, data=discovery
    )
    assert result["step_id"] == "pair"
    payload["id"] = "A2-OTHERTEST"
    wrong = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"code": encode_code(payload)}
    )
    assert wrong["errors"] == {"base": "code_wrong_device"}
    with (
        patch(
            "custom_components.rewise.config_flow.RewiseAirClient.status",
            return_value=status,
        ),
        patch("custom_components.rewise.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"code": code}
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()


async def test_wrong_model(hass, discovery):
    discovery.properties["model"] = "Other"
    result = await hass.config_entries.flow.async_init(
        "rewise", context={"source": "zeroconf"}, data=discovery
    )
    assert result["reason"] == "not_rewise_air"


async def test_discovery_updates_host(hass, discovery, code):
    entry = MockConfigEntry(
        domain="rewise", unique_id="A2-TEST01", data={"host": "192.0.2.2", "code": code}
    )
    entry.add_to_hass(hass)
    with patch.object(hass.config_entries, "async_reload", return_value=True):
        result = await hass.config_entries.flow.async_init(
            "rewise", context={"source": "zeroconf"}, data=discovery
        )
        assert result["reason"] == "already_configured"
        assert entry.data["host"] == "192.0.2.1"
        await hass.async_block_till_done()


@pytest.mark.parametrize(
    "source,step,reason",
    [
        ("reauth", "reauth_confirm", "reauth_successful"),
        ("reconfigure", "reconfigure", "reconfigure_successful"),
    ],
)
async def test_replace(hass, code, status, source, step, reason):
    entry = MockConfigEntry(
        domain="rewise",
        unique_id="A2-TEST01",
        data={"host": "192.0.2.1", "code": "old"},
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.rewise.config_flow.RewiseAirClient.status",
            return_value=status,
        ),
        patch.object(hass.config_entries, "async_reload", return_value=True),
    ):
        result = await hass.config_entries.flow.async_init(
            "rewise",
            context={"source": source, "entry_id": entry.entry_id},
            data=entry.data if source == "reauth" else None,
        )
        assert result["step_id"] == step
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"code": code}
        )
        assert result["reason"] == reason
        assert entry.data["code"] == code
        await hass.async_block_till_done()


@pytest.mark.parametrize("text", ["bad", "RWHA1.%%%"])
async def test_invalid(hass, text):
    result = await hass.config_entries.flow.async_init(
        "rewise", context={"source": "user"}, data={"host": "192.0.2.1", "code": text}
    )
    assert result["errors"] == {"base": "invalid_code"}


async def test_status_wrong_device(hass, code, status):
    status["device"]["id"] = "A2-OTHERTEST"
    with patch(
        "custom_components.rewise.config_flow.RewiseAirClient.status",
        return_value=status,
    ):
        result = await hass.config_entries.flow.async_init(
            "rewise",
            context={"source": "user"},
            data={"host": "192.0.2.1", "code": code},
        )
        assert result["errors"] == {"base": "code_wrong_device"}
