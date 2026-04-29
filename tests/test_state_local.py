import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.state_local import collect_local_state


class _FakeChannel:
    def __init__(self, *, index: int, role: int, settings: dict[str, object] | None = None) -> None:
        self.index = index
        self.role = role
        self.settings = dict(settings or {})


class _FakeNode:
    def __init__(self) -> None:
        self.localConfig = {"lora": {"modem_preset": "MEDIUM_FAST"}}
        self.moduleConfig = {"mqtt": {"address": "mqtt.meshtastic.org"}}
        self.channels = [
            _FakeChannel(index=0, role=1, settings={"name": "", "psk": b"default"}),
            _FakeChannel(index=1, role=2, settings={"name": "Meshyface", "psk": b"secret"}),
            _FakeChannel(index=2, role=0, settings={}),
        ]
        self.nodeNum = 0x1234ABCD
        self.position = {"latitude": 44.0, "longitude": -93.0}
        self.request_channels_calls: list[int] = []
        self.wait_for_config_calls: list[str] = []

    def requestChannels(self, startingIndex: int = 0) -> None:  # noqa: N802
        self.request_channels_calls.append(startingIndex)

    def waitForConfig(self, attribute: str = "channels") -> None:  # noqa: N802
        self.wait_for_config_calls.append(attribute)


class _FakeIface:
    def __init__(self) -> None:
        self.localNode = _FakeNode()
        self.myInfo = {"my_node_num": 0x1234ABCD}
        self.nodesByNum = {
            0x1234ABCD: {
                "num": 0x1234ABCD,
                "user": {"id": "!1234abcd", "longName": "Demo Relay"},
            }
        }


def test_collect_local_state_preserves_explicit_channel_roles() -> None:
    iface = _FakeIface()

    state = collect_local_state(iface)

    assert state["channels"] == [
        {"index": 0, "role": "PRIMARY", "settings": {"name": "", "psk": "64656661756c74"}},
        {"index": 1, "role": "SECONDARY", "settings": {"name": "Meshyface", "psk": "736563726574"}},
        {"index": 2, "role": "DISABLED", "settings": {}},
    ]


def test_collect_local_state_can_refresh_channels_before_serializing() -> None:
    iface = _FakeIface()

    collect_local_state(iface, refresh_channels=True)

    assert iface.localNode.request_channels_calls == [0]
    assert iface.localNode.wait_for_config_calls == ["channels"]
