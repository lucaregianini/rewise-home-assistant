"""Diagnostics with credentials and learned IR data removed."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import RewiseConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: RewiseConfigEntry
) -> dict[str, Any]:
    """Never include the original encoded code, which contains a password."""
    coordinator = entry.runtime_data
    return async_redact_data(
        {
            "status": coordinator.data,
            "connection": json.loads(json.dumps(asdict(coordinator.code))),
        },
        {
            "pass",
            "password",
            "user",
            "ir",
            "token",
            "url",
            "hostname",
            "ssid",
            "ip",
            "bssid",
        },
    )
