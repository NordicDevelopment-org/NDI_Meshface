import time
from collections.abc import Iterable
from string import hexdigits
from typing import Optional

from .helpers import format_epoch as _format_epoch
from .helpers import safe_json_loads as _safe_json_loads
from .helpers import to_float as _to_float
from .helpers import to_int as _to_int
from .history_time import clamp_future_unix as _clamp_future_unix
from .history_node_metrics import (
    build_metric_history_points as _build_metric_history_points_helper,
)
from .history_node_names import (
    build_name_history_points as _build_name_history_points_helper,
)
from .history_node_positions import (
    build_position_history_points as _build_position_history_points_helper,
)

_PACKET_HISTORY_MAX_ROWS = 200
_PACKET_HISTORY_TEXT_MAX_CHARS = 180
_PACKET_TYPE_ORDER = (
    "all",
    "chat",
    "telemetry",
    "position",
    "routing",
    "nodeinfo",
    "admin",
    "encrypted",
    "other",
)
_PACKET_SERIES_BUCKET_SECONDS = 60


def _empty_packet_series_payload() -> dict[str, object]:
    return {
        "available": True,
        "bucket_seconds": _PACKET_SERIES_BUCKET_SECONDS,
        "order": list(_PACKET_TYPE_ORDER),
        "series": {key: [] for key in _PACKET_TYPE_ORDER},
    }


def _is_hex_text(value: str) -> bool:
    return bool(value) and all(ch in hexdigits for ch in value)


def _normalize_node_id(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    if lowered in {"^all", "all", "broadcast", "!ffffffff", "ffffffff", "0xffffffff", "4294967295"}:
        return "^all"
    if text.startswith("!") and len(text) == 9 and _is_hex_text(text[1:]):
        return f"!{text[1:].lower()}"
    if len(text) == 8 and _is_hex_text(text):
        return f"!{text.lower()}"
    return text


def _packet_direction(
    *,
    node_id: str,
    from_id: str,
    to_id: str,
) -> str:
    if node_id and from_id == node_id:
        return "sent"
    if node_id and to_id == node_id:
        return "recv"
    return "other"


def _packet_hops(summary: dict[str, object], packet: dict[str, object]) -> int | None:
    direct_hops = _to_int(summary.get("hops"))
    if direct_hops is None:
        direct_hops = _to_int(packet.get("hops"))
    if direct_hops is not None and direct_hops >= 0:
        return int(direct_hops)

    hop_start = _to_int(summary.get("hop_start"))
    if hop_start is None:
        hop_start = _to_int(packet.get("hopStart"))
    hop_limit = _to_int(summary.get("hop_limit"))
    if hop_limit is None:
        hop_limit = _to_int(packet.get("hopLimit"))
    if hop_start is None or hop_limit is None:
        return None
    if hop_start < hop_limit:
        return None
    return int(hop_start - hop_limit)


def _packet_channel_text(
    summary: dict[str, object],
    packet: dict[str, object],
    decoded: dict[str, object],
) -> str | None:
    for candidate in (
        summary.get("channel"),
        packet.get("channel"),
        decoded.get("channel_index"),
        decoded.get("channelIndex"),
        decoded.get("channel"),
    ):
        as_int = _to_int(candidate)
        if as_int is not None and as_int >= 0:
            return f"Ch {int(as_int)}"
        text = str(candidate or "").strip()
        if text:
            return text
    return None


def _packet_text_preview(
    summary: dict[str, object],
    decoded: dict[str, object],
) -> str | None:
    text = ""
    for candidate in (
        summary.get("decoded_text"),
        decoded.get("text"),
    ):
        if isinstance(candidate, str) and candidate.strip():
            text = candidate.strip().replace("\r\n", "\n").replace("\r", "\n")
            break
    if not text and summary.get("is_reaction"):
        emoji = str(summary.get("emoji") or "").strip()
        return f"reaction {emoji}".strip()
    if not text:
        return None
    if len(text) <= _PACKET_HISTORY_TEXT_MAX_CHARS:
        return text
    return f"{text[: _PACKET_HISTORY_TEXT_MAX_CHARS - 3]}..."


def _collect_packet_history(
    *,
    node_id: str,
    packet_rows: Iterable[tuple[object, ...]],
    max_rows: int = _PACKET_HISTORY_MAX_ROWS,
) -> tuple[list[dict[str, object]], int]:
    now_unix = int(time.time())
    clean_node_id = _normalize_node_id(node_id)
    rows_cap = max(1, int(max_rows))
    entries: list[dict[str, object]] = []
    total_count = 0

    for row in packet_rows:
        created_unix = row[0] if len(row) > 0 else None
        summary_json = row[1] if len(row) > 1 else None
        packet_json = row[2] if len(row) > 2 else None

        summary = _safe_json_loads(summary_json, {})
        if not isinstance(summary, dict):
            summary = {}
        packet = _safe_json_loads(packet_json, {})
        if not isinstance(packet, dict):
            packet = {}
        decoded = packet.get("decoded")
        if not isinstance(decoded, dict):
            decoded = {}

        packet_time_unix = _extract_packet_time_unix(
            created_unix,
            summary,
            packet,
            now_unix=now_unix,
        )
        if packet_time_unix is None or packet_time_unix <= 0:
            continue

        from_id = str(
            summary.get("from")
            or summary.get("from_id")
            or packet.get("fromId")
            or packet.get("from_id")
            or packet.get("from")
            or ""
        ).strip()
        to_id = str(
            summary.get("to")
            or summary.get("to_id")
            or packet.get("toId")
            or packet.get("to_id")
            or packet.get("to")
            or ""
        ).strip()
        from_norm = _normalize_node_id(from_id)
        to_norm = _normalize_node_id(to_id)
        direction = _packet_direction(
            node_id=clean_node_id,
            from_id=from_norm,
            to_id=to_norm,
        )
        peer_id = (
            (to_id if direction == "sent" else from_id if direction == "recv" else "")
            or to_id
            or from_id
            or None
        )

        portnum = str(
            summary.get("portnum")
            or decoded.get("portnum")
            or packet.get("portnum")
            or ""
        ).strip()
        packet_id = _to_int(summary.get("packet_id"))
        if packet_id is None:
            packet_id = _to_int(packet.get("id"))
        hops = _packet_hops(summary, packet)
        rx_snr = _to_float(summary.get("rx_snr"))
        if rx_snr is None:
            rx_snr = _to_float(packet.get("rxSnr"))
        if rx_snr is None:
            rx_snr = _to_float(packet.get("rx_snr"))
        rx_rssi = _to_float(summary.get("rx_rssi"))
        if rx_rssi is None:
            rx_rssi = _to_float(packet.get("rxRssi"))
        if rx_rssi is None:
            rx_rssi = _to_float(packet.get("rx_rssi"))
        channel = _packet_channel_text(summary, packet, decoded)
        text = _packet_text_preview(summary, decoded)

        total_count += 1
        if len(entries) >= rows_cap:
            continue
        entries.append(
            {
                "time_unix": int(packet_time_unix),
                "time": _format_epoch(packet_time_unix),
                "direction": direction,
                "from_id": from_id or None,
                "to_id": to_id or None,
                "peer_id": peer_id,
                "portnum": portnum or None,
                "channel": channel,
                "hops": hops,
                "rx_snr": rx_snr,
                "rx_rssi": rx_rssi,
                "packet_id": packet_id,
                "text": text,
            }
        )

    return entries, total_count


def _extract_packet_time_unix(
    created_unix: object,
    summary_json: object,
    packet_json: object,
    *,
    now_unix: int,
) -> int | None:
    if isinstance(summary_json, dict):
        summary = summary_json
    else:
        summary = _safe_json_loads(summary_json, {})
    if isinstance(packet_json, dict):
        packet = packet_json
    else:
        packet = _safe_json_loads(packet_json, {})
    decoded = packet.get("decoded") if isinstance(packet, dict) else {}
    if not isinstance(decoded, dict):
        decoded = {}
    for candidate in (
        summary.get("rx_time_unix") if isinstance(summary, dict) else None,
        summary.get("rxTime") if isinstance(summary, dict) else None,
        packet.get("rxTime") if isinstance(packet, dict) else None,
        packet.get("rx_time_unix") if isinstance(packet, dict) else None,
        decoded.get("rx_time_unix"),
        created_unix,
    ):
        ts = _to_int(candidate)
        if ts is not None and ts > 0:
            clamped = _clamp_future_unix(
                ts,
                now_unix=now_unix,
                fallback_unix=created_unix,
                default_to_now=False,
            )
            if clamped > 0:
                return int(clamped)
            continue
    return None


def _collect_packet_timestamps(
    packet_rows: Iterable[tuple[object, ...]],
) -> list[int]:
    timestamps: set[int] = set()
    now_unix = int(time.time())
    for row in packet_rows:
        created_unix = row[0] if len(row) > 0 else None
        summary_json = row[1] if len(row) > 1 else None
        packet_json = row[2] if len(row) > 2 else None
        packet_time = _extract_packet_time_unix(
            created_unix,
            summary_json,
            packet_json,
            now_unix=now_unix,
        )
        if packet_time is None or packet_time <= 0:
            continue
        timestamps.add(packet_time)
    return sorted(timestamps)


def _build_packet_series_payload(
    packet_type_rows: Iterable[tuple[object, ...]],
) -> dict[str, object]:
    bucket_counts_by_bucket: dict[int, dict[str, int]] = {}
    for raw_row in packet_type_rows:
        if isinstance(raw_row, tuple):
            row = raw_row
        elif isinstance(raw_row, list):
            row = tuple(raw_row)
        else:
            try:
                row = tuple(raw_row)
            except Exception:
                continue
        if len(row) < 3:
            continue
        bucket = _to_int(row[0])
        packet_type = str(row[1] or "").strip().lower()
        packet_count = max(0, _to_int(row[2]) or 0)
        if bucket is None or bucket <= 0 or packet_count <= 0:
            continue
        clean_type = packet_type if packet_type in _PACKET_TYPE_ORDER else "other"
        bucket_counts = bucket_counts_by_bucket.setdefault(
            bucket,
            {key: 0 for key in _PACKET_TYPE_ORDER},
        )
        bucket_counts[clean_type] = int(bucket_counts.get(clean_type, 0)) + packet_count
        bucket_counts["all"] = int(bucket_counts.get("all", 0)) + packet_count

    if not bucket_counts_by_bucket:
        return _empty_packet_series_payload()

    return {
        "available": True,
        "bucket_seconds": _PACKET_SERIES_BUCKET_SECONDS,
        "order": list(_PACKET_TYPE_ORDER),
        "series": {
            key: [
                {
                    "bucket_unix": bucket,
                    "packet_count": int(bucket_counts.get(key, 0)),
                }
                for bucket, bucket_counts in sorted(bucket_counts_by_bucket.items())
                if int(bucket_counts.get(key, 0)) > 0
            ]
            for key in _PACKET_TYPE_ORDER
        },
    }


def build_node_history_payload(
    *,
    node_id: str,
    window_hours: int,
    metric_rows: Iterable[tuple[object, ...]],
    position_rows: Iterable[tuple[object, ...]],
    packet_rows: Iterable[tuple[object, ...]],
    packet_type_rows: Iterable[tuple[object, ...]],
) -> dict[str, object]:
    clean_node_id = str(node_id or "").strip()
    hours = max(1, int(window_hours))
    if not clean_node_id:
        return {
            "node_id": "",
            "window_hours": hours,
            "points": [],
            "positions": [],
            "name_history": [],
            "packet_timestamps": [],
            "packet_history": [],
            "packet_series": _empty_packet_series_payload(),
            "summary": {},
        }

    points: list[dict[str, object]] = []
    positions: list[dict[str, object]] = []
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

    metric_data = _build_metric_history_points_helper(metric_rows)
    points = metric_data["points"]
    total_packets = metric_data["total_packets"]
    first_bucket = metric_data["first_bucket"]
    last_bucket = metric_data["last_bucket"]
    last_seen = metric_data["last_seen"]
    snr_min_all = metric_data["snr_min"]
    snr_max_all = metric_data["snr_max"]
    rssi_min_all = metric_data["rssi_min"]
    rssi_max_all = metric_data["rssi_max"]

    position_data = _build_position_history_points_helper(position_rows)
    positions = position_data["positions"]
    trail_start = position_data["trail_start"]
    trail_end = position_data["trail_end"]
    packet_timestamps = _collect_packet_timestamps(packet_rows)
    packet_history, packet_history_total = _collect_packet_history(
        node_id=clean_node_id,
        packet_rows=packet_rows,
    )
    packet_series = _build_packet_series_payload(packet_type_rows)
    name_history = _build_name_history_points_helper(
        node_id=clean_node_id,
        packet_rows=packet_rows,
    )

    return {
        "node_id": clean_node_id,
        "window_hours": hours,
        "points": points,
        "positions": positions,
        "name_history": name_history,
        "packet_timestamps": packet_timestamps,
        "packet_history": packet_history,
        "packet_series": packet_series,
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
            "packet_history_count": len(packet_history),
            "packet_history_total": int(packet_history_total),
            "packet_history_truncated": bool(packet_history_total > len(packet_history)),
        },
    }
