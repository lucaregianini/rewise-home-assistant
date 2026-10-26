"""Serialized local HTTP requests to one Rewise Air A2."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

import aiohttp

from .const import BUSY_RETRY, MIN_GAP, TIMEOUT


class CannotConnect(Exception):
    """The Air A2 could not be reached or returned invalid data."""


class AuthFailed(Exception):
    """The Air A2 refused the credentials."""


class ApiError(Exception):
    """A structured error returned by the Air A2."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class RewiseAirClient:
    """One lock protects polls and commands, including retries."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        user: str,
        password: str,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._session = session
        self.host = host
        self._auth = aiohttp.BasicAuth(user, password)
        self._lock = asyncio.Lock()
        self._last_command: float | None = None
        self._clock = clock
        self._sleep = sleep

    async def status(self) -> dict[str, Any]:
        return await self._request("GET", "/api/v1/status", command=False)

    async def control(self, **fields: Any) -> dict[str, Any]:
        return await self._request("POST", "/api/v1/control", fields)

    async def extra(self, name: str, on: bool) -> dict[str, Any]:
        return await self._request(
            "POST", "/api/v1/ac-extra", {"extra": name, "on": on}
        )

    async def other_ac(
        self,
        protocol: str,
        model: int,
        power: bool,
        mode: str,
        fan: str,
        temperature: int,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/api/v1/ac-other",
            {
                "protocol": protocol,
                "model": model,
                "power": power,
                "mode": mode,
                "fan": fan,
                "temperatureC": temperature,
            },
        )

    async def ir_send(self, body: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/api/v1/ir/send", body)

    async def sensor(self) -> dict[str, Any]:
        return await self._request(
            "GET", "/api/v1/sensor", command=False, authenticated=False
        )

    async def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        command: bool = True,
        authenticated: bool = True,
    ) -> dict[str, Any]:
        async with self._lock:
            for attempt in range(2):
                if command and self._last_command is not None:
                    wait = self._last_command + MIN_GAP - self._clock()
                    if wait > 0:
                        await self._sleep(wait)
                try:
                    status, data = await self._send(method, path, body, authenticated)
                finally:
                    # A lost response may still mean IR was sent. Pace failed attempts too.
                    if command:
                        self._last_command = self._clock()
                if status == 401:
                    raise AuthFailed
                error = data.get("error")
                if not isinstance(error, dict):
                    error = {}
                if status == 409 and error.get("code") == "busy" and attempt == 0:
                    await self._sleep(BUSY_RETRY)
                    continue
                if status >= 400:
                    raise ApiError(
                        error.get("code", str(status)),
                        error.get("message", "Request failed"),
                    )
                return data
        raise CannotConnect

    async def _send(
        self, method: str, path: str, body: dict[str, Any] | None, authenticated: bool
    ) -> tuple[int, dict[str, Any]]:
        host = (
            f"[{self.host}]"
            if ":" in self.host
            and not self.host.startswith("[")
            and self.host.count(":") > 1
            else self.host
        )
        try:
            async with self._session.request(
                method,
                f"http://{host}{path}",
                json=body,
                auth=self._auth if authenticated else None,
                allow_redirects=False,
                timeout=aiohttp.ClientTimeout(total=TIMEOUT),
            ) as response:
                if response.status == 401:
                    return 401, {}
                data = await response.json(content_type=None)
                if not isinstance(data, dict):
                    raise CannotConnect
                if 300 <= response.status < 400:
                    raise CannotConnect
                return response.status, data
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise CannotConnect from err
