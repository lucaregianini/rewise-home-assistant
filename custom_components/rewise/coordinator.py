"""Poll the Air A2 and share state between its entities."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ApiError, AuthFailed, CannotConnect, RewiseAirClient
from .code import ConnectionCode
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


class RewiseCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """A shared status poll and a slower diagnostic poll."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: RewiseAirClient,
        code: ConnectionCode,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=SCAN_INTERVAL,
        )
        self.client = client
        self.code = code
        self.sensor_data: dict[str, Any] = {}
        self._sensor_at: float | None = None
        self._extras: tuple[bool, tuple[str, ...]] | None = None
        self._reload_pending = False

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self.client.status()
            if data.get("device", {}).get("id") != self.code.device_id:
                raise UpdateFailed("The address belongs to a different Rewise Air")
            if not all(
                isinstance(data.get(key), dict)
                for key in ("ac", "environment", "extras")
            ):
                raise UpdateFailed("Invalid Rewise Air status")
            now = time.monotonic()
            if self._sensor_at is None or now - self._sensor_at >= 300:
                self._sensor_at = now
                try:
                    self.sensor_data = await self.client.sensor()
                except (CannotConnect, ApiError):
                    self.sensor_data = {}
            extras = data["extras"]
            signature = (
                bool(extras.get("stateful")),
                tuple(sorted(extras.get("supported", []))),
            )
            if (
                self._extras is not None
                and signature != self._extras
                and not self._reload_pending
            ):
                self._reload_pending = True
                self.hass.async_create_task(
                    self.hass.config_entries.async_reload(self.config_entry.entry_id)
                )
            self._extras = signature
            return data
        except AuthFailed as err:
            raise ConfigEntryAuthFailed from err
        except (CannotConnect, ApiError) as err:
            raise UpdateFailed("Rewise Air did not answer") from err

    async def command(
        self,
        action: Callable[[], Awaitable[dict[str, Any]]],
        *,
        updates_status: bool = True,
    ) -> None:
        """Report actionable command errors without exposing credentials."""
        try:
            result = await action()
            if updates_status:
                self.async_set_updated_data(result)
        except AuthFailed as err:
            self.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="invalid_auth"
            ) from err
        except CannotConnect as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="cannot_connect"
            ) from err
        except ApiError as err:
            key = "busy" if err.code in ("busy", "ir_busy") else "command_failed"
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key=key
            ) from err
