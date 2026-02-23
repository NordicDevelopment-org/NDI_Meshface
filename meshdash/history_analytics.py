from datetime import datetime
from typing import Any, Dict, Iterable, Optional

from .helpers import format_epoch as _format_epoch, to_float as _to_float, to_int as _to_int


def build_node_history_payload(
    *,
    node_id: str,
    window_hours: int,
    metric_rows: Iterable[Any],
    position_rows: Iterable[Any],
) -> Dict[str, Any]:
    clean_node_id = str(node_id or "").strip()
    hours = max(1, int(window_hours))
    if not clean_node_id:
        return {
            "node_id": "",
            "window_hours": hours,
            "points": [],
            "positions": [],
            "summary": {},
        }

    points: list[Dict[str, Any]] = []
    positions: list[Dict[str, Any]] = []
    total_packets = 0
    snr_min_all: Optional[float] = None
    snr_max_all: Optional[float] = None
    rssi_min_all: Optional[float] = None
    rssi_max_all: Optional[float] = None
    first_bucket: Optional[int] = None
    last_bucket: Optional[int] = None
    last_seen: Optional[int] = None
    trail_start: Optional[int] = None
    trail_end: Optional[int] = None

    for row in reversed(list(metric_rows)):
        (
            bucket_unix,
            packet_count,
            snr_sum,
            snr_count,
            snr_min,
            snr_max,
            rssi_sum,
            rssi_count,
            rssi_min,
            rssi_max,
            hops_sum,
            hops_count,
            hops_min,
            hops_max,
            last_seen_unix,
        ) = row

        bucket = _to_int(bucket_unix)
        if bucket is None:
            continue

        packets = _to_int(packet_count) or 0
        total_packets += packets
        first_bucket = bucket if first_bucket is None else min(first_bucket, bucket)
        last_bucket = bucket if last_bucket is None else max(last_bucket, bucket)
        seen_val = _to_int(last_seen_unix)
        if seen_val is not None:
            last_seen = seen_val if last_seen is None else max(last_seen, seen_val)

        snr_count_i = _to_int(snr_count) or 0
        rssi_count_i = _to_int(rssi_count) or 0
        hops_count_i = _to_int(hops_count) or 0
        snr_avg = (_to_float(snr_sum) or 0.0) / snr_count_i if snr_count_i > 0 else None
        rssi_avg = (_to_float(rssi_sum) or 0.0) / rssi_count_i if rssi_count_i > 0 else None
        hops_avg = (_to_float(hops_sum) or 0.0) / hops_count_i if hops_count_i > 0 else None

        snr_min_v = _to_float(snr_min)
        snr_max_v = _to_float(snr_max)
        rssi_min_v = _to_float(rssi_min)
        rssi_max_v = _to_float(rssi_max)

        if snr_min_v is not None:
            snr_min_all = snr_min_v if snr_min_all is None else min(snr_min_all, snr_min_v)
        if snr_max_v is not None:
            snr_max_all = snr_max_v if snr_max_all is None else max(snr_max_all, snr_max_v)
        if rssi_min_v is not None:
            rssi_min_all = rssi_min_v if rssi_min_all is None else min(rssi_min_all, rssi_min_v)
        if rssi_max_v is not None:
            rssi_max_all = rssi_max_v if rssi_max_all is None else max(rssi_max_all, rssi_max_v)

        points.append(
            {
                "bucket_unix": bucket,
                "bucket_time": _format_epoch(bucket),
                "packet_count": packets,
                "avg_snr": round(snr_avg, 2) if snr_avg is not None else None,
                "min_snr": snr_min_v,
                "max_snr": snr_max_v,
                "avg_rssi": round(rssi_avg, 2) if rssi_avg is not None else None,
                "min_rssi": rssi_min_v,
                "max_rssi": rssi_max_v,
                "avg_hops": round(hops_avg, 2) if hops_avg is not None else None,
                "min_hops": _to_int(hops_min),
                "max_hops": _to_int(hops_max),
                "hops_samples": hops_count_i,
                "last_seen": _format_epoch(last_seen_unix),
            }
        )

    for created_unix, lat, lon, altitude, sats_in_view in reversed(list(position_rows)):
        point_unix = _to_int(created_unix)
        lat_f = _to_float(lat)
        lon_f = _to_float(lon)
        if point_unix is None or lat_f is None or lon_f is None:
            continue
        if not (-90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0):
            continue
        if lat_f == 0.0 and lon_f == 0.0:
            continue
        trail_start = point_unix if trail_start is None else min(trail_start, point_unix)
        trail_end = point_unix if trail_end is None else max(trail_end, point_unix)
        positions.append(
            {
                "time_unix": point_unix,
                "time": _format_epoch(point_unix),
                "lat": lat_f,
                "lon": lon_f,
                "altitude": _to_float(altitude),
                "sats_in_view": _to_int(sats_in_view),
            }
        )

    return {
        "node_id": clean_node_id,
        "window_hours": hours,
        "points": points,
        "positions": positions,
        "summary": {
            "total_packets": total_packets,
            "points": len(points),
            "first_bucket": _format_epoch(first_bucket),
            "last_bucket": _format_epoch(last_bucket),
            "last_seen": _format_epoch(last_seen),
            "snr_min": snr_min_all,
            "snr_max": snr_max_all,
            "rssi_min": rssi_min_all,
            "rssi_max": rssi_max_all,
            "trail_points": len(positions),
            "trail_start": _format_epoch(trail_start),
            "trail_end": _format_epoch(trail_end),
        },
    }


def build_online_activity_payload(
    *,
    window_hours: int,
    hour_rows: Iterable[Any],
    distinct_nodes: int,
    timezone_label: Optional[str] = None,
) -> Dict[str, Any]:
    hours = max(1, int(window_hours))
    tz_label = timezone_label or datetime.now().astimezone().tzname() or "local"

    points: list[Dict[str, Any]] = []
    by_hour: Dict[int, list[int]] = {hour: [] for hour in range(24)}
    total_online = 0
    max_online = 0
    first_bucket: Optional[int] = None
    last_bucket: Optional[int] = None

    for raw_bucket, raw_online in hour_rows:
        bucket = _to_int(raw_bucket)
        if bucket is None:
            continue
        online_nodes = max(0, _to_int(raw_online) or 0)
        local_dt = datetime.fromtimestamp(bucket)
        hour_local = local_dt.hour
        by_hour.setdefault(hour_local, []).append(online_nodes)
        total_online += online_nodes
        max_online = max(max_online, online_nodes)
        first_bucket = bucket if first_bucket is None else min(first_bucket, bucket)
        last_bucket = bucket if last_bucket is None else max(last_bucket, bucket)
        points.append(
            {
                "bucket_unix": bucket,
                "bucket_time": _format_epoch(bucket),
                "bucket_local": local_dt.strftime("%Y-%m-%d %H:00"),
                "hour_local": hour_local,
                "hour_label": f"{hour_local:02d}:00",
                "online_nodes": online_nodes,
            }
        )

    best_hour: Optional[int] = None
    best_avg: Optional[float] = None
    hourly_profile: list[Dict[str, Any]] = []
    for hour in range(24):
        samples = by_hour.get(hour, [])
        sample_count = len(samples)
        avg_online = (sum(samples) / sample_count) if sample_count > 0 else None
        peak_online = max(samples) if sample_count > 0 else 0
        if avg_online is not None:
            if best_avg is None or avg_online > best_avg + 1e-9:
                best_hour = hour
                best_avg = avg_online
            elif best_hour is not None and abs(avg_online - best_avg) <= 1e-9 and hour < best_hour:
                best_hour = hour
        hourly_profile.append(
            {
                "hour": hour,
                "label": f"{hour:02d}:00",
                "avg_online_nodes": round(avg_online, 2) if avg_online is not None else None,
                "sample_hours": sample_count,
                "peak_online_nodes": peak_online,
            }
        )

    sample_hours = len(points)
    avg_online_nodes = (total_online / sample_hours) if sample_hours > 0 else None

    return {
        "window_hours": hours,
        "timezone": "local",
        "timezone_label": tz_label,
        "points": points,
        "hourly_profile": hourly_profile,
        "summary": {
            "sample_hours": sample_hours,
            "distinct_nodes": int(distinct_nodes or 0),
            "max_online_nodes": max_online,
            "avg_online_nodes": round(avg_online_nodes, 2) if avg_online_nodes is not None else None,
            "best_hour": best_hour,
            "best_hour_label": f"{best_hour:02d}:00" if best_hour is not None else None,
            "best_hour_avg_online_nodes": round(best_avg, 2) if best_avg is not None else None,
            "window_start": _format_epoch(first_bucket),
            "window_end": _format_epoch(last_bucket),
        },
    }
