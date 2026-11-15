"""Find Rewise Air A2 devices on the network while the user adds the integration.

Home Assistant only starts listening for an integration's zeroconf types at boot.
After an install from the Marketplace (or HACS) without a restart, nothing has
been discovered yet, so the setup flow browses for the service itself.
"""

from __future__ import annotations

import asyncio
import logging

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

SERVICE_TYPE = "_smartachub._tcp.local."
MODEL = "Rewise Air A2"
BROWSE_SECONDS = 3
RESOLVE_MS = 3000


async def async_discover(hass: HomeAssistant) -> dict[str, str]:
    """Return {device id: host} for every Rewise Air A2 that answers mDNS."""
    try:
        from homeassistant.components import zeroconf
        from zeroconf import IPVersion, ServiceStateChange
        from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo

        aiozc = await zeroconf.async_get_async_instance(hass)
    except Exception:  # noqa: BLE001 - discovery is optional; manual setup remains
        _LOGGER.debug("mDNS unavailable, falling back to manual setup", exc_info=True)
        return {}

    names: set[str] = set()

    def _on_change(*, zeroconf, service_type, name, state_change) -> None:
        if state_change is not ServiceStateChange.Removed:
            names.add(name)

    found: dict[str, str] = {}
    try:
        browser = AsyncServiceBrowser(
            aiozc.zeroconf, [SERVICE_TYPE], handlers=[_on_change]
        )
        try:
            await asyncio.sleep(BROWSE_SECONDS)
        finally:
            await browser.async_cancel()
        for name in sorted(names):
            info = AsyncServiceInfo(SERVICE_TYPE, name)
            if not await info.async_request(aiozc.zeroconf, RESOLVE_MS):
                continue
            props = {
                k.decode(errors="ignore"): (v or b"").decode(errors="ignore")
                for k, v in info.properties.items()
            }
            if props.get("model") != MODEL or not props.get("id"):
                continue
            hosts = info.parsed_scoped_addresses(IPVersion.V4Only) or (
                info.parsed_scoped_addresses()
            )
            if hosts:
                found[props["id"]] = hosts[0]
    except Exception:  # noqa: BLE001
        _LOGGER.debug("mDNS browse for Rewise Air failed", exc_info=True)
    return found
