import asyncio

import pytest
from aiohttp import ClientSession

from custom_components.rewise.api import ApiError, CannotConnect, RewiseAirClient


class Clock:
    now = 0.0

    def time(self):
        return self.now

    async def sleep(self, seconds):
        self.now += seconds


async def test_command_gap_retry_and_poll(fake_air):
    host, requests, replies = fake_air
    clock = Clock()
    sent = []
    async with ClientSession() as session:
        client = RewiseAirClient(
            session, host, "admin", "test-pass-123", clock=clock.time, sleep=clock.sleep
        )
        original = client._send

        async def record(*args):
            if args[0] == "POST":
                sent.append(clock.now)
            return await original(*args)

        client._send = record
        await client.control(power=True)
        await client.status()
        await asyncio.gather(client.control(fan="low"), client.control(mode="cool"))
        replies.extend([(409, {"error": {"code": "busy"}}), (200, {"sent": True})])
        await client.ir_send({"raw": [9000, 4500, 560], "khz": 38})
        assert len(sent) == 5
        assert all(b - a >= 1.1 - 1e-9 for a, b in zip(sent, sent[1:]))
        assert sent[-1] - sent[-2] >= 1.2 - 1e-9
        replies.extend([(409, {"error": {"code": "busy"}})] * 2)
        with pytest.raises(ApiError):
            await client.control(power=False)
        assert len(replies) == 0


async def test_failure_is_paced(fake_air):
    host, _, _ = fake_air
    clock = Clock()
    async with ClientSession() as session:
        client = RewiseAirClient(
            session, host, "admin", "test-pass-123", clock=clock.time, sleep=clock.sleep
        )
        original = client._send

        async def lost(*args):
            raise CannotConnect

        client._send = lost
        with pytest.raises(CannotConnect):
            await client.control(power=True)
        client._send = original
        await client.control(power=False)
        assert clock.now == pytest.approx(1.1)
