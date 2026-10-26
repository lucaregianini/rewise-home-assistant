"""Discover and pair Rewise Air A2 devices."""
from __future__ import annotations
from typing import Any
import ipaddress
try:
    import probatio as vol
except ImportError:
    import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .api import ApiError, AuthFailed, CannotConnect, RewiseAirClient
from .code import ConnectionCode, InvalidCode, decode_code
from .const import CONF_CODE, DOMAIN

def valid_host(host: str) -> bool:
    """Accept a bare LAN host, never a URL with embedded credentials or paths."""
    if not host or any(c.isspace() or c in "/@?#" for c in host): return False
    if ":" in host:
        try: ipaddress.IPv6Address(host.strip("[]"))
        except ValueError: return False
    return True

class RewiseConfigFlow(ConfigFlow, domain=DOMAIN):
    """Pair by discovery or manually and replace stale codes."""
    VERSION = 1
    def __init__(self) -> None:
        self._host: str | None = None
        self._device_id: str | None = None
    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> ConfigFlowResult:
        props = discovery_info.properties
        if props.get("model") != "Rewise Air A2" or not props.get("id"):
            return self.async_abort(reason="not_rewise_air")
        self._host = discovery_info.host
        self._device_id = props["id"]
        await self.async_set_unique_id(self._device_id)
        self._abort_if_unique_id_configured(updates={CONF_HOST:self._host}, reload_on_update=True)
        self.context["title_placeholders"] = {"name":self._device_id}
        return await self.async_step_pair()
    async def _validate(self, host: str, text: str, expected: str | None) -> tuple[ConnectionCode | None, dict[str,str]]:
        if not valid_host(host): return None, {"base":"cannot_connect"}
        try:
            code = decode_code(text)
        except InvalidCode:
            return None, {"base":"invalid_code"}
        if expected is not None and code.device_id != expected:
            return None, {"base":"code_wrong_device"}
        client=RewiseAirClient(async_get_clientsession(self.hass),host,code.user,code.password)
        try:
            status=await client.status()
        except AuthFailed: return None, {"base":"invalid_auth"}
        except (CannotConnect, ApiError): return None, {"base":"cannot_connect"}
        if status.get("device",{}).get("id") != code.device_id:
            return None, {"base":"code_wrong_device"}
        return code, {}
    async def async_step_user(self, user_input: dict[str,Any] | None = None) -> ConfigFlowResult:
        errors={}
        if user_input is not None:
            host=user_input[CONF_HOST].strip()
            code,errors=await self._validate(host,user_input[CONF_CODE],None)
            if code is not None:
                await self.async_set_unique_id(code.device_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=code.name,data={CONF_HOST:host,CONF_CODE:user_input[CONF_CODE]})
        return self.async_show_form(step_id="user",data_schema=vol.Schema({vol.Required(CONF_HOST):str,vol.Required(CONF_CODE):str}),errors=errors)
    async def async_step_pair(self, user_input: dict[str,Any] | None = None) -> ConfigFlowResult:
        errors={}
        if user_input is not None:
            code,errors=await self._validate(self._host,user_input[CONF_CODE],self._device_id)
            if code is not None:
                return self.async_create_entry(title=code.name,data={CONF_HOST:self._host,CONF_CODE:user_input[CONF_CODE]})
        return self.async_show_form(step_id="pair",data_schema=vol.Schema({vol.Required(CONF_CODE):str}),errors=errors)
    async def async_step_reauth(self, entry_data: dict[str,Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()
    async def async_step_reauth_confirm(self, user_input: dict[str,Any] | None = None) -> ConfigFlowResult:
        return await self._replace("reauth_confirm",user_input)
    async def async_step_reconfigure(self, user_input: dict[str,Any] | None = None) -> ConfigFlowResult:
        return await self._replace("reconfigure",user_input)
    async def _replace(self, step: str, user_input: dict[str,Any] | None) -> ConfigFlowResult:
        entry=self._get_reauth_entry() if step == "reauth_confirm" else self._get_reconfigure_entry()
        errors={}
        if user_input is not None:
            code,errors=await self._validate(entry.data[CONF_HOST],user_input[CONF_CODE],entry.unique_id)
            if code is not None:
                await self.async_set_unique_id(code.device_id)
                self._abort_if_unique_id_mismatch()
                self.hass.config_entries.async_update_entry(entry,title=code.name)
                return self.async_update_reload_and_abort(entry,data_updates={CONF_CODE:user_input[CONF_CODE]},reload_even_if_entry_is_unchanged=True)
        return self.async_show_form(step_id=step,data_schema=vol.Schema({vol.Required(CONF_CODE):str}),errors=errors)
