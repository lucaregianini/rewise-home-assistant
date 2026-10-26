import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from aiohttp import web
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rewise.code import decode_code
from custom_components.rewise.coordinator import RewiseCoordinator


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def payload():
    return json.loads((Path(__file__).parent / "fixtures/code_v1.json").read_text())


@pytest.fixture
def code(payload):
    from custom_components.rewise.code import encode_code

    return encode_code(payload)


@pytest.fixture
def status():
    return {
        "apiVersion": 1,
        "device": {
            "id": "A2-TEST01",
            "model": "Rewise Air A2",
            "firmwareVersion": "0.3.4",
        },
        "ac": {
            "power": True,
            "temperatureC": 24,
            "mode": "cool",
            "fan": "auto",
            "protocol": "DAIKIN",
        },
        "environment": {"temperatureC": 25.1, "relativeHumidity": 52},
        "extras": {
            "supported": ["swingV", "turbo"],
            "stateful": True,
            "state": {"swingV": False, "turbo": False},
        },
        "cloud": {"connected": True},
    }


@pytest.fixture
async def fake_air(aiohttp_server, status, socket_enabled):
    requests = []
    replies = []

    async def handle(request):
        from aiohttp import BasicAuth

        body = await request.json() if request.can_read_body else None
        requests.append((request.path, body, request.headers.get("Authorization")))
        if (
            request.path != "/api/v1/sensor"
            and request.headers.get("Authorization")
            != BasicAuth("admin", "test-pass-123").encode()
        ):
            return web.Response(status=401, text="Unauthorized")
        if replies:
            code, data = replies.pop(0)
            return web.json_response(data, status=code)
        if request.path == "/api/v1/sensor":
            return web.json_response({"rssi": -55, "firmware": "0.3.4"})
        if request.path == "/api/v1/control":
            status["ac"].update(body)
        if request.path == "/api/v1/ac-extra":
            status["extras"]["state"][body["extra"]] = body["on"]
        return web.json_response(
            {"sent": True}
            if request.path in ("/api/v1/ac-other", "/api/v1/ir/send")
            else status
        )

    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", handle)
    server = await aiohttp_server(app)
    return f"127.0.0.1:{server.port}", requests, replies


@pytest.fixture
def coordinator(hass, code, status):
    client = AsyncMock()
    client.control.return_value = status
    client.extra.return_value = status
    entry = MockConfigEntry(domain="rewise", data={"host": "192.0.2.1", "code": code})
    entry.add_to_hass(hass)
    coordinator = RewiseCoordinator(hass, entry, client, decode_code(code))
    coordinator.async_set_updated_data(status)
    return coordinator
