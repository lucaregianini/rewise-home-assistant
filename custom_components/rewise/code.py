"""Decode the password-bearing connection code from the Rewise app."""
from __future__ import annotations

import base64
import binascii
import json
import zlib
from dataclasses import dataclass, field
from typing import Any

PREFIX = "RWHA1."
MAX_BYTES = 1_000_000

class InvalidCode(ValueError):
    """The connection code is invalid."""

@dataclass(frozen=True)
class OtherAC:
    key: str
    name: str
    protocol: str
    model: int

@dataclass(frozen=True)
class LearnedButton:
    key: str
    name: str
    ir: dict[str, Any]

@dataclass(frozen=True)
class IRDevice:
    key: str
    name: str
    kind: str
    buttons: tuple[LearnedButton, ...]

@dataclass(frozen=True)
class ConnectionCode:
    device_id: str
    name: str
    user: str
    password: str = field(repr=False)
    other_acs: tuple[OtherAC, ...] = ()
    devices: tuple[IRDevice, ...] = ()

def _text(data: dict[str, Any], key: str) -> str:
    value = data[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(key)
    return value

def decode_code(text: str) -> ConnectionCode:
    """Decode raw DEFLATE, as written by Apple's Compression framework."""
    text = "".join(text.split())
    if not text.startswith(PREFIX):
        raise InvalidCode("prefix")
    body = text[len(PREFIX):]
    if len(body) > MAX_BYTES * 2:
        raise InvalidCode("size")
    try:
        raw = base64.b64decode(body + "=" * (-len(body) % 4), altchars=b"-_", validate=True)
        inflater = zlib.decompressobj(-15)
        inflated = inflater.decompress(raw, MAX_BYTES + 1)
        if len(inflated) > MAX_BYTES or not inflater.eof or inflater.unused_data:
            raise ValueError("size or trailing data")
        data = json.loads(inflated)
    except (ValueError, binascii.Error, zlib.error) as err:
        raise InvalidCode("format") from err
    if not isinstance(data, dict) or type(data.get("v")) is not int or data["v"] != 1:
        raise InvalidCode("version")
    try:
        other_acs = []
        for ac in data.get("otherACs", []):
            model = ac.get("model", -1)
            if type(model) is not int:
                raise ValueError("model")
            other_acs.append(OtherAC(_text(ac,"key"), _text(ac,"name"), _text(ac,"protocol"), model))
        devices = []
        for device in data.get("devices", []):
            buttons = []
            for button in device["buttons"]:
                ir = button["ir"]
                if not isinstance(ir, dict) or not ir:
                    raise ValueError("ir")
                buttons.append(LearnedButton(_text(button,"key"), _text(button,"name"), ir))
            devices.append(IRDevice(_text(device,"key"), _text(device,"name"), _text(device,"kind"), tuple(buttons)))
        keys = [ac.key for ac in other_acs]
        button_keys = [button.key for device in devices for button in device.buttons]
        if len(keys) != len(set(keys)) or len(button_keys) != len(set(button_keys)):
            raise ValueError("duplicate keys")
        return ConnectionCode(_text(data,"id"), _text(data,"name"), _text(data,"user"), _text(data,"pass"), tuple(other_acs), tuple(devices))
    except (KeyError, TypeError, ValueError, AttributeError) as err:
        raise InvalidCode("fields") from err

def encode_code(data: dict[str, Any]) -> str:
    """Encode a fake payload for interoperability tests."""
    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
    raw = compressor.compress(json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode()) + compressor.flush()
    return PREFIX + base64.urlsafe_b64encode(raw).decode().rstrip("=")
