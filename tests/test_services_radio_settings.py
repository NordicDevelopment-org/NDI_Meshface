from meshdash.api_input_radio import RadioSettingsRequest
from meshdash.services_radio_settings import apply_radio_settings


class _FakeLock:
    def __init__(self):
        self.acquire_calls = 0
        self.release_calls = 0

    def acquire(self):
        self.acquire_calls += 1

    def release(self):
        self.release_calls += 1


class _FakeNode:
    def __init__(self):
        self.localConfig = object()
        self.fixed_position_calls = []
        self.remove_fixed_position_calls = 0

    def setFixedPosition(self, lat, lon, alt):
        self.fixed_position_calls.append((lat, lon, alt))

    def removeFixedPosition(self):
        self.remove_fixed_position_calls += 1


def _iface_with_local_node(node):
    class _Iface:
        pass

    iface = _Iface()
    iface.localNode = node
    return iface


def test_apply_radio_settings_sets_fixed_position_without_lora_reboot():
    node = _FakeNode()
    lock = _FakeLock()
    response = apply_radio_settings(
        RadioSettingsRequest(
            lora={},
            fixed_position={"latitude": 44.9801, "longitude": -93.2636, "altitude": 288},
            clear_fixed_position=False,
        ),
        iface=_iface_with_local_node(node),
        send_lock=lock,
    )

    assert response["ok"] is True
    assert response["reboot_expected"] is False
    assert response["applied"]["fixed_position"]["latitude"] == 44.9801
    assert response["applied"]["fixed_position"]["longitude"] == -93.2636
    assert response["applied"]["fixed_position"]["altitude"] == 288
    assert node.fixed_position_calls == [(44.9801, -93.2636, 288)]
    assert lock.acquire_calls == 1
    assert lock.release_calls == 1


def test_apply_radio_settings_clears_fixed_position():
    node = _FakeNode()
    lock = _FakeLock()
    response = apply_radio_settings(
        RadioSettingsRequest(
            lora={},
            fixed_position={},
            clear_fixed_position=True,
        ),
        iface=_iface_with_local_node(node),
        send_lock=lock,
    )

    assert response["ok"] is True
    assert response["applied"]["clear_fixed_position"] is True
    assert node.remove_fixed_position_calls == 1
    assert lock.acquire_calls == 1
    assert lock.release_calls == 1


def test_apply_radio_settings_rejects_conflicting_fixed_position_requests():
    node = _FakeNode()
    response = apply_radio_settings(
        RadioSettingsRequest(
            lora={},
            fixed_position={"latitude": 44.98, "longitude": -93.26},
            clear_fixed_position=True,
        ),
        iface=_iface_with_local_node(node),
        send_lock=_FakeLock(),
    )

    assert response["ok"] is False
    assert "Cannot set and clear fixed position" in str(response["error"])
    assert node.fixed_position_calls == []
    assert node.remove_fixed_position_calls == 0

