import json
from pathlib import Path

import pytest

from custom_components.rewise.code import InvalidCode, decode_code, encode_code

FIXTURES = Path(__file__).parent / "fixtures"


def test_shared_vector():
    payload = json.loads((FIXTURES / "code_v1.json").read_text())
    expected = decode_code((FIXTURES / "code_v1.txt").read_text())
    assert decode_code(encode_code(payload)) == expected
    assert expected.password == "test-pass-123"
    assert expected.other_acs[0].protocol == "DAIKIN"
    assert expected.devices[0].buttons[1].ir == {"raw": [9000, 4500, 560], "khz": 38}
    assert "test-pass-123" not in repr(expected)
    assert decode_code(" \n" + encode_code(payload) + " ") == expected


@pytest.mark.parametrize("text", ["", "RWHA2.abc", "RWHA1.%%%", "RWHA1.eA", "RWHA1."])
def test_bad_format(text):
    with pytest.raises(InvalidCode):
        decode_code(text)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"v": 2},
        {"v": True},
        {"v": 1},
        {"v": 1, "id": None, "name": "Room", "user": "admin", "pass": "fake"},
    ],
)
def test_bad_fields(payload):
    with pytest.raises(InvalidCode):
        decode_code(encode_code(payload))


def test_extras_are_optional(payload):
    assert decode_code(encode_code(payload)).extras is None
    payload["extras"] = []
    assert decode_code(encode_code(payload)).extras == ()
    payload["extras"] = ["turbo", 3]
    with pytest.raises(InvalidCode):
        decode_code(encode_code(payload))
