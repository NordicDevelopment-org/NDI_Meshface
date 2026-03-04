from types import SimpleNamespace

import pytest

from meshdash.api_input_channels import ChannelSettingsRequest
from meshdash.services_channels import (
    _acquire_lock,
    _compute_last_active_index,
    _ensure_channels_loaded,
    _get_local_node,
    _role_name,
    _role_value,
    apply_channel_settings,
)


class _FakeRole:
    DISABLED = 0
    PRIMARY = 1
    SECONDARY = 2

    @classmethod
    def Name(cls, value: int) -> str:
        mapping = {
            cls.DISABLED: "DISABLED",
            cls.PRIMARY: "PRIMARY",
            cls.SECONDARY: "SECONDARY",
        }
        if int(value) not in mapping:
            raise ValueError("bad role")
        return mapping[int(value)]


class _FakeChannelPb2:
    class Channel:
        Role = _FakeRole


class _FakeSettings:
    def __init__(self):
        self.name = ""
        self.uplink_enabled = False
        self.downlink_enabled = False
        self.psk = b"existing"


class _FakeModuleSettings:
    def __init__(self):
        self.is_muted = False
        self.position_precision = 0


class _FakeChannel:
    def __init__(self, index: int, role: int):
        self.index = index
        self.role = role
        self.settings = _FakeSettings()
        self.module_settings = _FakeModuleSettings()


class _FakeNode:
    def __init__(
        self,
        *,
        channels,
        has_write_channel: bool = True,
        write_error: Exception | None = None,
        export_url: str = "https://mesh.example/ch",
        export_error: Exception | None = None,
    ):
        self.channels = channels
        self.request_calls = []
        self.wait_calls = []
        self.write_calls = []
        self._write_error = write_error
        self._export_url = export_url
        self._export_error = export_error
        if has_write_channel:
            self.writeChannel = self._write_channel

    def requestChannels(self, idx=0):
        self.request_calls.append(idx)
        if self.channels is None:
            self.channels = [_FakeChannel(0, _FakeRole.PRIMARY)]

    def waitForConfig(self, key):
        self.wait_calls.append(key)

    def _write_channel(self, idx: int):
        self.write_calls.append(int(idx))
        if self._write_error is not None:
            raise self._write_error

    def getURL(self, includeAll=True):
        if self._export_error is not None:
            raise self._export_error
        suffix = "all=1" if includeAll else "all=0"
        return f"{self._export_url}?{suffix}"


class _FakeLock:
    def __init__(self):
        self.acquire_calls = 0
        self.release_calls = 0

    def acquire(self):
        self.acquire_calls += 1

    def release(self):
        self.release_calls += 1


def _iface_with_local(node):
    return SimpleNamespace(localNode=node)


def test_get_local_node_and_channel_helpers():
    local = object()
    assert _get_local_node(_iface_with_local(local)) is local

    fallback = object()
    iface = SimpleNamespace(localNode=None, getNode=lambda _id: fallback)
    assert _get_local_node(iface) is fallback

    with pytest.raises(RuntimeError, match="no local node"):
        _get_local_node(SimpleNamespace())

    eager_node = _FakeNode(channels=[_FakeChannel(0, _FakeRole.PRIMARY)])
    assert _ensure_channels_loaded(eager_node) is eager_node.channels

    lazy_node = _FakeNode(channels=None)
    loaded = _ensure_channels_loaded(lazy_node)
    assert isinstance(loaded, list)
    assert lazy_node.request_calls
    assert lazy_node.wait_calls == ["channels"]

    with pytest.raises(RuntimeError, match="not loaded"):
        _ensure_channels_loaded(SimpleNamespace(channels=None, requestChannels=None))


def test_role_last_active_and_lock_helpers():
    assert _role_value(_FakeChannelPb2, "primary") == _FakeRole.PRIMARY
    with pytest.raises(ValueError):
        _role_value(_FakeChannelPb2, "bad")

    assert _role_name(_FakeChannelPb2, 2) == "SECONDARY"
    broken_pb2 = SimpleNamespace(Channel=SimpleNamespace(Role=SimpleNamespace(Name=lambda _value: (_ for _ in ()).throw(ValueError("bad")))))
    assert _role_name(broken_pb2, 9) == "9"

    channels = [_FakeChannel(0, _FakeRole.PRIMARY), _FakeChannel(1, _FakeRole.SECONDARY), object()]
    assert _compute_last_active_index(_FakeChannelPb2, channels) == 1

    lock = _FakeLock()
    locked, release = _acquire_lock(lock)
    assert locked is True
    assert callable(release)
    release()
    assert lock.acquire_calls == 1
    assert lock.release_calls == 1
    assert _acquire_lock(object()) == (False, None)


def test_apply_channel_settings_export_url_paths(monkeypatch):
    monkeypatch.setattr("meshdash.services_channels._import_channel_pb2", lambda: _FakeChannelPb2)
    node = _FakeNode(channels=[_FakeChannel(0, _FakeRole.PRIMARY)])

    hidden = apply_channel_settings(
        ChannelSettingsRequest(action="export_url", include_all=False),
        iface=_iface_with_local(node),
        send_lock=_FakeLock(),
        show_secrets=False,
    )
    assert hidden["ok"] is False

    no_get = apply_channel_settings(
        ChannelSettingsRequest(action="export_url"),
        iface=SimpleNamespace(localNode=SimpleNamespace(channels=node.channels)),
        send_lock=_FakeLock(),
        show_secrets=True,
    )
    assert no_get["ok"] is False
    assert "getURL" in str(no_get["error"])

    fail_node = _FakeNode(channels=node.channels, export_error=RuntimeError("fail"))
    failed = apply_channel_settings(
        ChannelSettingsRequest(action="export_url"),
        iface=_iface_with_local(fail_node),
        send_lock=_FakeLock(),
        show_secrets=True,
    )
    assert failed["ok"] is False
    assert "Export failed" in str(failed["error"])

    ok = apply_channel_settings(
        ChannelSettingsRequest(action="export_url", include_all=False),
        iface=_iface_with_local(node),
        send_lock=_FakeLock(),
        show_secrets=True,
    )
    assert ok["ok"] is True
    assert ok["action"] == "export_url"
    assert ok["url"].endswith("all=0")


def test_apply_channel_settings_disable_paths(monkeypatch):
    monkeypatch.setattr("meshdash.services_channels._import_channel_pb2", lambda: _FakeChannelPb2)
    channels = [_FakeChannel(0, _FakeRole.PRIMARY), _FakeChannel(1, _FakeRole.SECONDARY)]
    node = _FakeNode(channels=channels)
    iface = _iface_with_local(node)

    missing = apply_channel_settings(
        ChannelSettingsRequest(action="disable"),
        iface=iface,
        send_lock=_FakeLock(),
        show_secrets=True,
    )
    assert missing["ok"] is False
    assert "required" in str(missing["error"])

    bad_zero = apply_channel_settings(
        ChannelSettingsRequest(action="disable", channel_index=0),
        iface=iface,
        send_lock=_FakeLock(),
        show_secrets=True,
    )
    assert bad_zero["ok"] is False

    out_of_order = apply_channel_settings(
        ChannelSettingsRequest(action="disable", channel_index=2),
        iface=iface,
        send_lock=_FakeLock(),
        show_secrets=True,
    )
    assert out_of_order["ok"] is False
    assert out_of_order.get("last_active_index") == 1

    channels[1].role = _FakeRole.PRIMARY
    primary_block = apply_channel_settings(
        ChannelSettingsRequest(action="disable", channel_index=1),
        iface=iface,
        send_lock=_FakeLock(),
        show_secrets=True,
    )
    assert primary_block["ok"] is False
    channels[1].role = _FakeRole.SECONDARY

    lock = _FakeLock()
    ok = apply_channel_settings(
        ChannelSettingsRequest(action="disable", channel_index=1),
        iface=iface,
        send_lock=lock,
        show_secrets=True,
    )
    assert ok["ok"] is True
    assert ok["action"] == "disable"
    assert node.write_calls == [1]
    assert lock.acquire_calls == 1
    assert lock.release_calls == 1
    assert channels[1].role == _FakeRole.DISABLED


def test_apply_channel_settings_upsert_validation_and_success(monkeypatch):
    monkeypatch.setattr("meshdash.services_channels._import_channel_pb2", lambda: _FakeChannelPb2)

    channels = [
        _FakeChannel(0, _FakeRole.PRIMARY),
        _FakeChannel(1, _FakeRole.SECONDARY),
        _FakeChannel(2, _FakeRole.DISABLED),
        _FakeChannel(3, _FakeRole.DISABLED),
    ]
    node = _FakeNode(channels=channels)
    iface = _iface_with_local(node)

    unsupported = apply_channel_settings(
        ChannelSettingsRequest(action="unknown"),
        iface=iface,
        send_lock=_FakeLock(),
        show_secrets=True,
    )
    assert unsupported["ok"] is False

    out_of_range = apply_channel_settings(
        ChannelSettingsRequest(action="upsert", channel_index=99),
        iface=iface,
        send_lock=_FakeLock(),
        show_secrets=True,
    )
    assert out_of_range["ok"] is False
    assert "out of range" in str(out_of_range["error"])

    gap_error = apply_channel_settings(
        ChannelSettingsRequest(action="upsert", channel_index=3, settings={"name": "Late"}),
        iface=iface,
        send_lock=_FakeLock(),
        show_secrets=True,
    )
    assert gap_error["ok"] is False
    assert "consecutive" in str(gap_error["error"])

    bad_role = apply_channel_settings(
        ChannelSettingsRequest(action="upsert", channel_index=1, role="bad"),
        iface=iface,
        send_lock=_FakeLock(),
        show_secrets=True,
    )
    assert bad_role["ok"] is False

    no_fields = apply_channel_settings(
        ChannelSettingsRequest(action="upsert", channel_index=1),
        iface=iface,
        send_lock=_FakeLock(),
        show_secrets=True,
    )
    assert no_fields["ok"] is False
    assert "No valid fields" in str(no_fields["error"])

    need_name = apply_channel_settings(
        ChannelSettingsRequest(action="upsert", channel_index=2, settings={"name": ""}),
        iface=iface,
        send_lock=_FakeLock(),
        show_secrets=True,
    )
    assert need_name["ok"] is False
    assert "name is required" in str(need_name["error"])

    write_fail_node = _FakeNode(channels=channels, write_error=RuntimeError("write fail"))
    write_fail = apply_channel_settings(
        ChannelSettingsRequest(
            action="upsert",
            channel_index=1,
            settings={
                "name": "Ops",
                "uplink_enabled": True,
                "downlink_enabled": True,
                "psk": "<redacted>",
                "module_settings": {"is_muted": True, "position_precision": 3},
            },
        ),
        iface=_iface_with_local(write_fail_node),
        send_lock=_FakeLock(),
        show_secrets=True,
    )
    assert write_fail["ok"] is False
    assert "Write failed" in str(write_fail["error"])
    assert write_fail["applied_fields"]

    success = apply_channel_settings(
        ChannelSettingsRequest(
            action="upsert",
            channel_index=1,
            settings={
                "name": "Ops",
                "uplink_enabled": True,
                "downlink_enabled": True,
                "psk": "<redacted>",
                "module_settings": {"is_muted": True, "position_precision": 3},
            },
        ),
        iface=iface,
        send_lock=_FakeLock(),
        show_secrets=True,
    )
    assert success["ok"] is True
    assert success["action"] == "upsert"
    assert success["role"] == "SECONDARY"
    assert "settings.name" in success["applied_fields"]
    assert "settings.psk" in success["ignored_fields"]


def test_apply_channel_settings_handles_missing_protobuf_and_write_support(monkeypatch):
    monkeypatch.setattr("meshdash.services_channels._import_channel_pb2", lambda: (_ for _ in ()).throw(RuntimeError("pb missing")))
    no_pb = apply_channel_settings(
        ChannelSettingsRequest(action="upsert"),
        iface=_iface_with_local(_FakeNode(channels=[])),
        send_lock=_FakeLock(),
        show_secrets=True,
    )
    assert no_pb["ok"] is False
    assert "protobuf unavailable" in str(no_pb["error"])

    monkeypatch.setattr("meshdash.services_channels._import_channel_pb2", lambda: _FakeChannelPb2)
    no_write = apply_channel_settings(
        ChannelSettingsRequest(action="upsert"),
        iface=_iface_with_local(_FakeNode(channels=[_FakeChannel(0, _FakeRole.PRIMARY)], has_write_channel=False)),
        send_lock=_FakeLock(),
        show_secrets=True,
    )
    assert no_write["ok"] is False
    assert "writeChannel" in str(no_write["error"])
