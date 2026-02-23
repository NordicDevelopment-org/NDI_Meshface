from typing import Any, Dict, Optional, Tuple

from .helpers_core import to_float as _to_float
from .helpers_core import to_int as _to_int


def extract_reply_id(decoded: Any) -> Optional[int]:
    if not isinstance(decoded, dict):
        return None
    for key in ("replyId", "reply_id"):
        value = _to_int(decoded.get(key))
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
        as_int = _to_int(clean)
        if as_int is not None:
            return as_int if as_int > 0 else None
        return ord(clean[0])

    as_int = _to_int(raw)
    if as_int is None or as_int <= 0:
        return None
    return as_int


def calculate_hops(hop_start: Any, hop_limit: Any) -> Optional[int]:
    start = _to_int(hop_start)
    limit = _to_int(hop_limit)
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
        lat = _to_float(position.get("latitudeI"))
        lat = lat * 1e-7 if lat is not None else None
    if lon is None and position.get("longitudeI") is not None:
        lon = _to_float(position.get("longitudeI"))
        lon = lon * 1e-7 if lon is not None else None

    if lat is None and position.get("latitude_i") is not None:
        lat = _to_float(position.get("latitude_i"))
        lat = lat * 1e-7 if lat is not None else None
    if lon is None and position.get("longitude_i") is not None:
        lon = _to_float(position.get("longitude_i"))
        lon = lon * 1e-7 if lon is not None else None

    lat_f = _to_float(lat)
    lon_f = _to_float(lon)
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

        altitude = _to_float(candidate.get("altitude"))
        if altitude is None:
            altitude = _to_float(candidate.get("altitude_m"))
        if altitude is None:
            altitude = _to_float(candidate.get("altitudeM"))

        sats = _to_int(candidate.get("satsInView"))
        if sats is None:
            sats = _to_int(candidate.get("sats_in_view"))
        if sats is None:
            sats = _to_int(candidate.get("satellites"))

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
            level_f = _to_float(raw)
            if level_f is None:
                continue
            level = int(round(level_f))
            if 0 <= level <= 100:
                return level
    return None
