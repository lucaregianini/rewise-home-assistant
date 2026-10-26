from unittest.mock import Mock

from custom_components.rewise.button import (
    RewiseExtraButton,
)
from custom_components.rewise.button import (
    async_setup_entry as setup_button,
)
from custom_components.rewise.switch import (
    RewiseExtraSwitch,
)
from custom_components.rewise.switch import (
    async_setup_entry as setup_switch,
)


async def test_stateful(coordinator, hass):
    switch = RewiseExtraSwitch(coordinator, "swingV")
    assert switch.is_on is False
    await switch.async_turn_on()
    coordinator.client.extra.assert_awaited_with("swingV", True)
    await switch.async_turn_off()
    coordinator.client.extra.assert_awaited_with("swingV", False)
    entry = Mock(runtime_data=coordinator)
    add = Mock()
    await setup_switch(hass, entry, add)
    assert len(add.call_args.args[0]) == 2


async def test_toggle(coordinator, hass):
    coordinator.data["extras"]["stateful"] = False
    button = RewiseExtraButton(coordinator, "turbo")
    await button.async_press()
    coordinator.client.extra.assert_awaited_with("turbo", True)
    entry = Mock(runtime_data=coordinator)
    add = Mock()
    await setup_switch(hass, entry, add)
    add.assert_not_called()
    await setup_button(hass, entry, add)
    assert len(add.call_args.args[0]) == 4
