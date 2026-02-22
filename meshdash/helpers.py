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


def extract_reply_id(decoded: Any) -> Optional[int]:
    if not isinstance(decoded, dict):
        return None
    for key in ("replyId", "reply_id"):
        value = to_int(decoded.get(key))
        if value is not None and value > 0:
            return value
    return None


def extract_emoji_codepoint(decoded: Any) -> Optional[int]:
    if not isinstance(decoded, dict):
        return None
    raw = decoded.get("emoji")
    if raw is None:
        return None

    if isinstance(raw, str):
        clean = raw.strip()
        if not clean:
            return None
        as_int = to_int(clean)
        if as_int is not None:
            return as_int if as_int > 0 else None
        return ord(clean[0])

    as_int = to_int(raw)
    if as_int is None or as_int <= 0:
        return None
    return as_int


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


def calculate_hops(hop_start: Any, hop_limit: Any) -> Optional[int]:
    start = to_int(hop_start)
    limit = to_int(hop_limit)
    if start is None or limit is None:
        return None
    hops = start - limit
    if hops < 0:
        return None
    return hops


def extract_position_fields(position: Any) -> Optional[Tuple[float, float]]:
    if not isinstance(position, dict):
        return None

    lat = position.get("latitude")
    lon = position.get("longitude")
    if lat is None:
        lat = position.get("lat")
    if lon is None:
        lon = position.get("lon")

    if lat is None and position.get("latitudeI") is not None:
        lat = to_float(position.get("latitudeI"))
        lat = lat * 1e-7 if lat is not None else None
    if lon is None and position.get("longitudeI") is not None:
        lon = to_float(position.get("longitudeI"))
        lon = lon * 1e-7 if lon is not None else None

    if lat is None and position.get("latitude_i") is not None:
        lat = to_float(position.get("latitude_i"))
        lat = lat * 1e-7 if lat is not None else None
    if lon is None and position.get("longitude_i") is not None:
        lon = to_float(position.get("longitude_i"))
        lon = lon * 1e-7 if lon is not None else None

    lat_f = to_float(lat)
    lon_f = to_float(lon)
    if lat_f is None or lon_f is None:
        return None
    if lat_f == 0.0 and lon_f == 0.0:
        return None
    if not (-90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0):
        return None
    return lat_f, lon_f


def extract_packet_position(packet: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(packet, dict):
        return None

    candidates: list[Dict[str, Any]] = []
    decoded = packet.get("decoded")
    if isinstance(decoded, dict):
        for key in ("position", "gps", "location"):
            candidate = decoded.get(key)
            if isinstance(candidate, dict):
                candidates.append(candidate)
        candidates.append(decoded)

    for key in ("position", "gps", "location"):
        candidate = packet.get(key)
        if isinstance(candidate, dict):
            candidates.append(candidate)
    candidates.append(packet)

    for candidate in candidates:
        coords = extract_position_fields(candidate)
        if coords is None:
            continue

        altitude = to_float(candidate.get("altitude"))
        if altitude is None:
            altitude = to_float(candidate.get("altitude_m"))
        if altitude is None:
            altitude = to_float(candidate.get("altitudeM"))

        sats = to_int(candidate.get("satsInView"))
        if sats is None:
            sats = to_int(candidate.get("sats_in_view"))
        if sats is None:
            sats = to_int(candidate.get("satellites"))

        out: Dict[str, Any] = {
            "lat": coords[0],
            "lon": coords[1],
        }
        if altitude is not None:
            out["altitude"] = altitude
        if sats is not None and sats >= 0:
            out["sats_in_view"] = sats
        return out
    return None


def extract_packet_battery_level(packet: Dict[str, Any]) -> Optional[int]:
    if not isinstance(packet, dict):
        return None

    candidates: list[Dict[str, Any]] = []
    decoded = packet.get("decoded")
    if isinstance(decoded, dict):
        telemetry = decoded.get("telemetry")
        if isinstance(telemetry, dict):
            candidates.append(telemetry)
            metrics = telemetry.get("deviceMetrics") or telemetry.get("device_metrics")
            if isinstance(metrics, dict):
                candidates.append(metrics)
        metrics = decoded.get("deviceMetrics") or decoded.get("device_metrics") or decoded.get("metrics")
        if isinstance(metrics, dict):
            candidates.append(metrics)
        candidates.append(decoded)

    telemetry = packet.get("telemetry")
    if isinstance(telemetry, dict):
        candidates.append(telemetry)
        metrics = telemetry.get("deviceMetrics") or telemetry.get("device_metrics")
        if isinstance(metrics, dict):
            candidates.append(metrics)
    metrics = packet.get("deviceMetrics") or packet.get("device_metrics") or packet.get("metrics")
    if isinstance(metrics, dict):
        candidates.append(metrics)
    candidates.append(packet)

    for candidate in candidates:
        for key in ("batteryLevel", "battery_level", "batteryPercent", "battery_percent", "battery"):
            raw = candidate.get(key)
            if raw is None:
                continue
            level_f = to_float(raw)
            if level_f is None:
                continue
            level = int(round(level_f))
            if 0 <= level <= 100:
                return level
    return None


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
