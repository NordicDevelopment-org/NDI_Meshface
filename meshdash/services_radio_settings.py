from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from .api_input_radio import RadioSettingsRequest


def _is_scalar_json(value: object) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"1", "true", "yes", "y", "on"}:
            return True
        if v in {"0", "false", "no", "n", "off"}:
            return False
    return bool(value)


def _coerce_int(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(float(value.strip()))
    return int(value)  # type: ignore[arg-type]


def _coerce_float(value: object) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value.strip())
    return float(value)  # type: ignore[arg-type]


def _apply_field_update(msg: Any, field_name: str, value: object) -> None:
    """Best-effort apply a field update on a protobuf message.

    We rely on protobuf descriptors for safe enum conversion.
    """

    # Protobuf messages should have a DESCRIPTOR.
    desc = getattr(msg, "DESCRIPTOR", None)
    if desc is None or not hasattr(desc, "fields_by_name"):
        # Fall back to plain setattr; might work for some wrappers.
        setattr(msg, field_name, value)
        return

    field_desc = desc.fields_by_name.get(field_name)
    if field_desc is None:
        raise ValueError(f"Unknown field '{field_name}'")

    # Repeated fields
    if getattr(field_desc, "label", None) == field_desc.LABEL_REPEATED:  # type: ignore[attr-defined]
        if isinstance(value, (str, bytes)) or not isinstance(value, Iterable):
            raise ValueError(f"Field '{field_name}' expects a list")
        if not all(_is_scalar_json(v) for v in value):
            raise ValueError(f"Field '{field_name}' list contains unsupported values")
        container = getattr(msg, field_name)
        try:
            # RepeatedScalarContainer supports clear/extend
            container.clear()
        except Exception:
            # Some containers don't have clear
            del container[:]
        try:
            container.extend(value)
        except Exception:
            for v in value:
                container.append(v)
        return

    # Message fields (nested)
    if getattr(field_desc, "type", None) == field_desc.TYPE_MESSAGE:  # type: ignore[attr-defined]
        if not isinstance(value, Mapping):
            raise ValueError(f"Field '{field_name}' expects an object")
        sub = getattr(msg, field_name)
        for k, v in value.items():
            if not isinstance(k, str):
                continue
            _apply_field_update(sub, k, v)
        return

    # Enum fields
    if getattr(field_desc, "type", None) == field_desc.TYPE_ENUM:  # type: ignore[attr-defined]
        if isinstance(value, str):
            enum_value = field_desc.enum_type.values_by_name.get(value)
            if enum_value is None:
                raise ValueError(f"Invalid enum value '{value}' for field '{field_name}'")
            setattr(msg, field_name, enum_value.number)
            return
        setattr(msg, field_name, _coerce_int(value))
        return

    # Scalar types
    ftype = getattr(field_desc, "type", None)
    if ftype in {field_desc.TYPE_BOOL}:  # type: ignore[attr-defined]
        setattr(msg, field_name, _coerce_bool(value))
        return
    if ftype in {
        field_desc.TYPE_INT32,
        field_desc.TYPE_SINT32,
        field_desc.TYPE_SFIXED32,
        field_desc.TYPE_INT64,
        field_desc.TYPE_SINT64,
        field_desc.TYPE_SFIXED64,
        field_desc.TYPE_UINT32,
        field_desc.TYPE_FIXED32,
        field_desc.TYPE_UINT64,
        field_desc.TYPE_FIXED64,
    }:  # type: ignore[attr-defined]
        setattr(msg, field_name, _coerce_int(value))
        return
    if ftype in {field_desc.TYPE_FLOAT, field_desc.TYPE_DOUBLE}:  # type: ignore[attr-defined]
        setattr(msg, field_name, _coerce_float(value))
        return
    if ftype in {field_desc.TYPE_STRING}:  # type: ignore[attr-defined]
        setattr(msg, field_name, str(value))
        return

    # Fallback
    setattr(msg, field_name, value)


def _apply_updates_to_message(msg: Any, updates: Mapping[str, object]) -> tuple[list[str], list[str]]:
    applied: list[str] = []
    ignored: list[str] = []
    for key, value in updates.items():
        if not isinstance(key, str):
            continue
        if value is None:
            ignored.append(key)
            continue
        try:
            _apply_field_update(msg, key, value)
            applied.append(key)
        except Exception:
            ignored.append(key)
    return applied, ignored


def _get_local_node(iface: object) -> Any:
    node = getattr(iface, "localNode", None)
    if node is not None:
        return node
    get_node = getattr(iface, "getNode", None)
    if callable(get_node):
        return get_node("^local")
    raise RuntimeError("Interface has no local node")


def apply_radio_settings(
    request: RadioSettingsRequest,
    *,
    iface: object,
    send_lock: object,
) -> dict[str, object]:
    """Apply radio settings (currently: LoRa config) to the connected local node."""

    lora_updates = request.lora or {}
    if not lora_updates:
        return {"ok": False, "error": "No settings provided"}

    node = _get_local_node(iface)
    local_config = getattr(node, "localConfig", None)
    if local_config is None:
        return {"ok": False, "error": "Local config is not available"}

    lora_cfg = getattr(local_config, "lora", None)
    if lora_cfg is None:
        return {"ok": False, "error": "LoRa config is not available"}

    applied_fields, ignored_fields = _apply_updates_to_message(lora_cfg, lora_updates)
    if not applied_fields:
        return {
            "ok": False,
            "error": "No valid fields to apply",
            "ignored_fields": ignored_fields,
        }

    # Apply on radio. LoRa config changes typically trigger a reboot.
    try:
        lock = send_lock
        # Best-effort support for threading.Lock-like objects.
        acquire = getattr(lock, "acquire", None)
        release = getattr(lock, "release", None)
        if callable(acquire) and callable(release):
            acquire()
            locked = True
        else:
            locked = False

        try:
            begin_tx = getattr(node, "beginSettingsTransaction", None)
            if callable(begin_tx):
                try:
                    begin_tx()
                except Exception:
                    pass

            write_cfg = getattr(node, "writeConfig", None)
            if not callable(write_cfg):
                return {"ok": False, "error": "Meshtastic node does not support writeConfig()"}
            write_cfg("lora")

            commit_tx = getattr(node, "commitSettingsTransaction", None)
            if callable(commit_tx):
                try:
                    commit_tx()
                except Exception:
                    pass
        finally:
            if locked:
                release()
    except Exception as exc:
        return {"ok": False, "error": f"Write failed: {exc}", "applied_fields": applied_fields}

    return {
        "ok": True,
        "applied": {"lora": {k: lora_updates.get(k) for k in applied_fields}},
        "applied_fields": applied_fields,
        "ignored_fields": ignored_fields,
        "reboot_expected": True,
    }
