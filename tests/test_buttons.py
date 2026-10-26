from custom_components.rewise.button import RewiseLearnedButton


async def test_exact_body(coordinator):
    for button in coordinator.code.devices[0].buttons:
        entity = RewiseLearnedButton(coordinator, "TV", button)
        await entity.async_press()
        coordinator.client.ir_send.assert_awaited_with(button.ir)
        assert entity.unique_id == f"A2-TEST01_btn_{button.key}"
