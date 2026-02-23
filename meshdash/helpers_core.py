import json
import os
import shutil
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

try:
    from google.protobuf.json_format import MessageToDict as _protobuf_message_to_dict
    from google.protobuf.message import Message as _protobuf_message_type
except Exception:
    _protobuf_message_type = None
    _protobuf_message_to_dict = None


def to_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def format_epoch(epoch_value: Any) -> Optional[str]:
    epoch = to_int(epoch_value)
    if epoch is None or epoch <= 0:
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def safe_json_loads(value: str, default: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def message_to_dict(value: Any) -> Any:
    if (
        _protobuf_message_type is not None
        and _protobuf_message_to_dict is not None
        and isinstance(value, _protobuf_message_type)
    ):
        return _protobuf_message_to_dict(value, preserving_proto_field_name=True)
    return None


def to_jsonable(value: Any, depth: int = 0) -> Any:
    if depth > 12:
        return "<max-depth>"
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, bytes):
        return value.hex()
    as_message = message_to_dict(value)
    if as_message is not None:
        return to_jsonable(as_message, depth + 1)
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for key, val in value.items():
            out[str(key)] = to_jsonable(val, depth + 1)
        return out
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item, depth + 1) for item in value]
    return str(value)


def is_sensitive_key(key: str, sensitive_field_names: set[str]) -> bool:
    key_l = key.lower()
    if key_l in sensitive_field_names:
        return True
    return key_l.endswith("_password") or key_l.endswith("_private_key")


def redact_secrets(
    value: Any,
    sensitive_field_names: set[str],
    parent_key: Optional[str] = None,
) -> Any:
    if parent_key and is_sensitive_key(parent_key, sensitive_field_names):
        return "<redacted>"
    if isinstance(value, dict):
        return {
            key: redact_secrets(val, sensitive_field_names, key)
            for key, val in value.items()
        }
    if isinstance(value, list):
        return [redact_secrets(item, sensitive_field_names, parent_key) for item in value]
    return value


def emoji_from_codepoint(codepoint: Optional[int]) -> Optional[str]:
    value = to_int(codepoint)
    if value is None or value <= 0:
        return None
    try:
        return chr(value)
    except (OverflowError, ValueError):
        return None


def normalize_single_emoji(value: Any) -> Tuple[Optional[str], Optional[int]]:
    if value is None:
        return None, None
    text = str(value).strip()
    if not text:
        return None, None

    as_int = to_int(text)
    if as_int is not None and as_int > 0:
        emoji = emoji_from_codepoint(as_int)
        if emoji:
            return emoji, as_int
        return None, None

    codepoint = ord(text[0])
    emoji = emoji_from_codepoint(codepoint)
    if emoji:
        return emoji, codepoint
    return None, None


def disk_space_info(path: Optional[str]) -> Dict[str, Any]:
    probe = os.path.abspath(os.path.expanduser(path or "."))
    if os.path.isfile(probe):
        probe = os.path.dirname(probe) or "."
    try:
        usage = shutil.disk_usage(probe)
        total = int(usage.total)
        free = int(usage.free)
        used = int(usage.used)
        free_pct = round((free / total) * 100.0, 1) if total > 0 else None
        used_pct = round((used / total) * 100.0, 1) if total > 0 else None
        return {
            "path": probe,
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "free_pct": free_pct,
            "used_pct": used_pct,
        }
    except Exception as exc:
        return {"path": probe, "error": str(exc)}
