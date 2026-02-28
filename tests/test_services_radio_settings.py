import pytest

from meshdash.api_input_radio import RadioSettingsRequest
from meshdash.services_radio_settings import (
    _apply_field_update,
    _apply_updates_to_message,
    _get_local_node,
    apply_radio_settings,
)


class _EnumValue:
    def __init__(self, number: int):
        self.number = number


class _EnumType:
    def __init__(self, values_by_name: dict[str, _EnumValue]):
        self.values_by_name = values_by_name


class _FieldDesc:
    LABEL_OPTIONAL = 1
    LABEL_REPEATED = 3

    TYPE_DOUBLE = 1
    TYPE_FLOAT = 2
    TYPE_INT64 = 3
    TYPE_UINT64 = 4
    TYPE_INT32 = 5
    TYPE_FIXED64 = 6
    TYPE_FIXED32 = 7
    TYPE_BOOL = 8
    TYPE_STRING = 9
    TYPE_MESSAGE = 11
    TYPE_UINT32 = 13
    TYPE_ENUM = 14
    TYPE_SFIXED32 = 15
    TYPE_SFIXED64 = 16
    TYPE_SINT32 = 17
    TYPE_SINT64 = 18

    def __init__(
        self,
        *,
        label: int = LABEL_OPTIONAL,
        type_: int = TYPE_STRING,
        enum_type: _EnumType | None = None,
    ):
        self.label = label
        self.type = type_
        self.enum_type = enum_type


class _Descriptor:
    def __init__(self, fields_by_name: dict[str, _FieldDesc]):
        self.fields_by_name = fields_by_name


class _NestedMessage:
    DESCRIPTOR = _Descriptor(
        {
            "sub_enabled": _FieldDesc(type_=_FieldDesc.TYPE_BOOL),
        }
    )

    def __init__(self):
        self.sub_enabled = True


class _LoraMessage:
    DESCRIPTOR = _Descriptor(
        {
            "hop_limit": _FieldDesc(type_=_FieldDesc.TYPE_INT32),
            "tx_power": _FieldDesc(type_=_FieldDesc.TYPE_FLOAT),
            "enabled": _FieldDesc(type_=_FieldDesc.TYPE_BOOL),
            "name": _FieldDesc(type_=_FieldDesc.TYPE_STRING),
            "mode": _FieldDesc(
                type_=_FieldDesc.TYPE_ENUM,
                enum_type=_EnumType({"FAST": _EnumValue(2)}),
            ),
            "channels": _FieldDesc(
                label=_FieldDesc.LABEL_REPEATED,
                type_=_FieldDesc.TYPE_INT32,
            ),
            "nested": _FieldDesc(type_=_FieldDesc.TYPE_MESSAGE),
            "passthrough": _FieldDesc(type_=999),
        }
    )

    def __init__(self):
        self.hop_limit = 0
        self.tx_power = 0.0
        self.enabled = False
        self.name = ""
        self.mode = 0
        self.channels = [99]
        self.nested = _NestedMessage()
        self.passthrough = None


class _LocalConfig:
    def __init__(self, lora: _LoraMessage | None):
        self.lora = lora


class _FakeNode:
    def __init__(
        self,
        *,
        has_local_config: bool = True,
        has_lora: bool = True,
        has_write: bool = True,
        write_error: Exception | None = None,
        begin_error: bool = False,
        commit_error: bool = False,
    ):
        self.localConfig = _LocalConfig(_LoraMessage() if has_lora else None) if has_local_config else None
        self.begin_calls = 0
        self.write_calls: list[str] = []
        self.commit_calls = 0
        self._write_error = write_error
        self._begin_error = begin_error
        self._commit_error = commit_error
        if not has_write:
            self.writeConfig = None

    def beginSettingsTransaction(self):
        self.begin_calls += 1
        if self._begin_error:
            raise RuntimeError("begin failed")

    def writeConfig(self, section: str):
        self.write_calls.append(section)
        if self._write_error is not None:
            raise self._write_error

    def commitSettingsTransaction(self):
        self.commit_calls += 1
        if self._commit_error:
            raise RuntimeError("commit failed")


class _FakeLock:
    def __init__(self):
        self.acquire_calls = 0
        self.release_calls = 0

    def acquire(self):
        self.acquire_calls += 1

    def release(self):
        self.release_calls += 1


def _iface_with_local_node(node: object):
    class _Iface:
        pass

    iface = _Iface()
    iface.localNode = node
    return iface


def _iface_with_get_node(node: object):
    class _Iface:
        def __init__(self, local: object):
            self._local = local

        def getNode(self, node_id: str):
            assert node_id == "^local"
            return self._local

    return _Iface(node)


def test_apply_field_update_without_descriptor_uses_setattr():
    class _Plain:
        pass

    plain = _Plain()
    _apply_field_update(plain, "answer", 42)
    assert plain.answer == 42


def test_apply_field_update_repeated_and_enum_validation_errors():
    lora = _LoraMessage()

    with pytest.raises(ValueError, match="expects a list"):
        _apply_field_update(lora, "channels", "not-a-list")

    with pytest.raises(ValueError, match="unsupported values"):
        _apply_field_update(lora, "channels", [1, {"bad": True}])

    with pytest.raises(ValueError, match="Invalid enum value"):
        _apply_field_update(lora, "mode", "SLOW")


def test_apply_updates_to_message_tracks_applied_and_ignored_fields():
    lora = _LoraMessage()
    applied, ignored = _apply_updates_to_message(
        lora,
        {
            "hop_limit": "3",
            "unknown_field": "x",
            "none_field": None,
            123: "skip",
        },
    )

    assert applied == ["hop_limit"]
    assert set(ignored) == {"unknown_field", "none_field"}
    assert lora.hop_limit == 3


def test_get_local_node_prefers_localnode_then_getnode():
    local = object()
    assert _get_local_node(_iface_with_local_node(local)) is local
    assert _get_local_node(_iface_with_get_node(local)) is local


def test_get_local_node_raises_without_local_accessors():
    with pytest.raises(RuntimeError, match="no local node"):
        _get_local_node(object())


def test_apply_radio_settings_success_converts_types_and_writes():
    node = _FakeNode()
    lock = _FakeLock()
    response = apply_radio_settings(
        RadioSettingsRequest(
            lora={
                "hop_limit": "3.0",
                "tx_power": "14.5",
                "enabled": "yes",
                "name": 1234,
                "mode": "FAST",
                "channels": [1, 2, 3],
                "nested": {"sub_enabled": "0"},
                "passthrough": {"free": "form"},
                "unknown_field": "x",
                "none_field": None,
            }
        ),
        iface=_iface_with_local_node(node),
        send_lock=lock,
    )

    lora = node.localConfig.lora
    assert response["ok"] is True
    assert set(response["applied_fields"]) == {
        "hop_limit",
        "tx_power",
        "enabled",
        "name",
        "mode",
        "channels",
        "nested",
        "passthrough",
    }
    assert set(response["ignored_fields"]) == {"unknown_field", "none_field"}
    assert response["reboot_expected"] is True
    assert lora.hop_limit == 3
    assert lora.tx_power == 14.5
    assert lora.enabled is True
    assert lora.name == "1234"
    assert lora.mode == 2
    assert lora.channels == [1, 2, 3]
    assert lora.nested.sub_enabled is False
    assert lora.passthrough == {"free": "form"}
    assert node.begin_calls == 1
    assert node.write_calls == ["lora"]
    assert node.commit_calls == 1
    assert lock.acquire_calls == 1
    assert lock.release_calls == 1


def test_apply_radio_settings_handles_missing_input_or_config():
    empty = apply_radio_settings(
        RadioSettingsRequest(lora={}),
        iface=_iface_with_local_node(_FakeNode()),
        send_lock=_FakeLock(),
    )
    assert empty["ok"] is False
    assert "No settings provided" in str(empty["error"])

    missing_local_config = apply_radio_settings(
        RadioSettingsRequest(lora={"hop_limit": 3}),
        iface=_iface_with_local_node(_FakeNode(has_local_config=False)),
        send_lock=_FakeLock(),
    )
    assert missing_local_config["ok"] is False
    assert "Local config is not available" in str(missing_local_config["error"])

    missing_lora = apply_radio_settings(
        RadioSettingsRequest(lora={"hop_limit": 3}),
        iface=_iface_with_local_node(_FakeNode(has_lora=False)),
        send_lock=_FakeLock(),
    )
    assert missing_lora["ok"] is False
    assert "LoRa config is not available" in str(missing_lora["error"])


def test_apply_radio_settings_rejects_when_no_valid_fields():
    response = apply_radio_settings(
        RadioSettingsRequest(lora={"unknown_field": "x", "none_field": None}),
        iface=_iface_with_local_node(_FakeNode()),
        send_lock=_FakeLock(),
    )

    assert response["ok"] is False
    assert "No valid fields to apply" in str(response["error"])
    assert set(response["ignored_fields"]) == {"unknown_field", "none_field"}


def test_apply_radio_settings_handles_write_failures_and_missing_writeconfig():
    missing_write_node = _FakeNode(has_write=False)
    missing_write_lock = _FakeLock()
    missing_write = apply_radio_settings(
        RadioSettingsRequest(lora={"hop_limit": 3}),
        iface=_iface_with_local_node(missing_write_node),
        send_lock=missing_write_lock,
    )
    assert missing_write["ok"] is False
    assert "does not support writeConfig" in str(missing_write["error"])
    assert missing_write_lock.acquire_calls == 1
    assert missing_write_lock.release_calls == 1

    write_error_node = _FakeNode(write_error=RuntimeError("boom"))
    write_error_lock = _FakeLock()
    write_error = apply_radio_settings(
        RadioSettingsRequest(lora={"hop_limit": 3}),
        iface=_iface_with_local_node(write_error_node),
        send_lock=write_error_lock,
    )
    assert write_error["ok"] is False
    assert "Write failed: boom" in str(write_error["error"])
    assert write_error["applied_fields"] == ["hop_limit"]
    assert write_error_lock.acquire_calls == 1
    assert write_error_lock.release_calls == 1


def test_apply_radio_settings_allows_getnode_and_non_lock_object():
    node = _FakeNode(begin_error=True, commit_error=True)
    response = apply_radio_settings(
        RadioSettingsRequest(lora={"hop_limit": 7}),
        iface=_iface_with_get_node(node),
        send_lock=object(),
    )

    assert response["ok"] is True
    assert response["applied_fields"] == ["hop_limit"]
    assert node.begin_calls == 1
    assert node.commit_calls == 1
    assert node.write_calls == ["lora"]
