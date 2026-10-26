import pytest
from aiohttp import ClientSession

from custom_components.rewise.api import (
    ApiError,
    AuthFailed,
    CannotConnect,
    RewiseAirClient,
)


async def test_requests(fake_air):
    host, requests, replies = fake_air
    async with ClientSession() as session:
        client = RewiseAirClient(session, host, "admin", "test-pass-123")
        assert (await client.status())["device"]["id"] == "A2-TEST01"
        assert (await client.control(power=False))["ac"]["power"] is False
        assert (await client.sensor())["rssi"] == -55
        assert requests[-1][2] is None
        replies.append(
            (422, {"error": {"code": "extra_not_supported", "message": "No extra"}})
        )
        with pytest.raises(ApiError, match="No extra"):
            await client.extra("bad", True)
        wrong = RewiseAirClient(session, host, "admin", "wrong-fake-password")
        with pytest.raises(AuthFailed):
            await wrong.status()


async def test_invalid_response(fake_air):
    host, _, replies = fake_air
    async with ClientSession() as session:
        client = RewiseAirClient(session, host, "admin", "test-pass-123")
        replies.append((200, []))
        with pytest.raises(CannotConnect):
            await client.status()


async def test_transport_failure(socket_enabled):
    async with ClientSession() as session:
        client = RewiseAirClient(session, "127.0.0.1:1", "admin", "test-pass-123")
        with pytest.raises(CannotConnect):
            await client.status()


async def test_error_body_without_details(fake_air):
    host, _, replies = fake_air
    async with ClientSession() as session:
        client = RewiseAirClient(session, host, "admin", "test-pass-123")
        replies.append((500, {"error": "Internal"}))
        with pytest.raises(ApiError) as err:
            await client.control(power=True)
        assert err.value.code == "500"
