from __future__ import annotations

from collections.abc import Iterable, Mapping
from contextlib import contextmanager
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


@contextmanager
def _send_lock_guard(send_lock: object):
    lock = send_lock
    acquire = getattr(lock, "acquire", None)
    release = getattr(lock, "release", None)
    locked = False
    if callable(acquire) and callable(release):
        acquire()
        locked = True
    try:
        yield
    finally:
        if locked:
            release()


def _apply_fixed_position(
    node: object,
    fixed_position: Mapping[str, object],
) -> dict[str, object]:
    setter = getattr(node, "setFixedPosition", None)
    if not callable(setter):
        raise RuntimeError("Meshtastic node does not support setFixedPosition()")

    lat = _coerce_float(fixed_position.get("latitude"))
    lon = _coerce_float(fixed_position.get("longitude"))
    altitude_raw = fixed_position.get("altitude")
    altitude = _coerce_int(altitude_raw) if altitude_raw is not None else 0

    setter(lat, lon, altitude)
    return {
        "latitude": lat,
        "longitude": lon,
        "altitude": altitude,
    }


def _clear_fixed_position(node: object) -> None:
    clearer = getattr(node, "removeFixedPosition", None)
    if not callable(clearer):
        raise RuntimeError("Meshtastic node does not support removeFixedPosition()")
    clearer()


def apply_radio_settings(
    request: RadioSettingsRequest,
    *,
    iface: object,
    send_lock: object,
) -> dict[str, object]:
    """Apply radio settings to the connected local node."""

    lora_updates = request.lora or {}
    fixed_position = request.fixed_position or {}
    clear_fixed_position = bool(request.clear_fixed_position)

    if fixed_position and clear_fixed_position:
        return {
            "ok": False,
            "error": "Cannot set and clear fixed position in the same request",
        }

    if not lora_updates and not fixed_position and not clear_fixed_position:
        return {"ok": False, "error": "No settings provided"}

    node = _get_local_node(iface)
    ignored_fields: list[str] = []
    applied_lora_fields: list[str] = []
    applied: dict[str, object] = {}
    reboot_expected = False

    try:
        with _send_lock_guard(send_lock):
            if lora_updates:
                local_config = getattr(node, "localConfig", None)
                if local_config is None:
                    return {"ok": False, "error": "Local config is not available"}

                lora_cfg = getattr(local_config, "lora", None)
                if lora_cfg is None:
                    return {"ok": False, "error": "LoRa config is not available"}

                lora_applied, lora_ignored = _apply_updates_to_message(lora_cfg, lora_updates)
                ignored_fields.extend(lora_ignored)
                if not lora_applied and not (fixed_position or clear_fixed_position):
                    return {
                        "ok": False,
                        "error": "No valid fields to apply",
                        "ignored_fields": ignored_fields,
                    }
                if lora_applied:
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
                    applied_lora_fields = lora_applied
                    applied["lora"] = {k: lora_updates.get(k) for k in lora_applied}
                    reboot_expected = True

            if fixed_position:
                applied["fixed_position"] = _apply_fixed_position(node, fixed_position)

            if clear_fixed_position:
                _clear_fixed_position(node)
                applied["clear_fixed_position"] = True
    except Exception as exc:
        payload: dict[str, object] = {"ok": False, "error": f"Write failed: {exc}"}
        if applied_lora_fields:
            payload["applied_fields"] = applied_lora_fields
        return payload

    if not applied and ignored_fields:
        return {
            "ok": False,
            "error": "No valid fields to apply",
            "ignored_fields": ignored_fields,
        }

    return {
        "ok": True,
        "applied": applied,
        "applied_fields": applied_lora_fields,
        "ignored_fields": ignored_fields,
        "reboot_expected": reboot_expected,
    }
