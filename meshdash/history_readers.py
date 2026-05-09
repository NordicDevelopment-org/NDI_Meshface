from collections.abc import Iterable

from .file_transfer_protocol import is_file_transfer_protocol_chat_entry as _is_file_transfer_protocol_chat_entry
from .helpers import safe_json_loads as _safe_json_loads, to_float as _to_float, to_int as _to_int

HistoryRow = tuple[object, ...]
HistoryPayload = dict[str, object]

def decode_recent_packets_rows(rows: Iterable[HistoryRow]) -> list[HistoryPayload]:
    out: list[HistoryPayload] = []
    for summary_json, packet_json in reversed(list(rows)):
        summary = _safe_json_loads(summary_json, {})
        if not isinstance(summary, dict):
            continue
        packet = _safe_json_loads(packet_json, {})
        out.append({"summary": summary, "packet": packet})
    return out


def decode_recent_chat_rows(rows: Iterable[HistoryRow]) -> list[HistoryPayload]:
    out: list[HistoryPayload] = []
    for (message_json,) in reversed(list(rows)):
        entry = _safe_json_loads(message_json, {})
        if isinstance(entry, dict) and not _is_file_transfer_protocol_chat_entry(entry):
            out.append(entry)
    return out


def decode_chat_page_rows(rows: Iterable[HistoryRow]) -> list[HistoryPayload]:
    out: list[HistoryPayload] = []
    for row in reversed(list(rows)):
        if len(row) < 3:
            continue
        history_id, created_unix, message_json = row[:3]
        entry = _safe_json_loads(message_json, {})
        if not isinstance(entry, dict) or _is_file_transfer_protocol_chat_entry(entry):
            continue
        entry["_history_id"] = _to_int(history_id)
        entry["_history_created_unix"] = _to_int(created_unix)
        out.append(entry)
    return out


def decode_connections_rows(rows: Iterable[HistoryRow]) -> list[HistoryPayload]:
    out: list[HistoryPayload] = []
    for row in rows:
        if len(row) < 9:
            continue
        (
            from_id,
            to_id,
            first_seen_unix,
            last_seen_unix,
            seen_count,
            portnums_json,
            last_hops,
            hops_sum,
            hops_count,
        ) = row[:9]
        if len(row) >= 17:
            (
                snr_sum,
                snr_count,
                snr_min,
                snr_max,
                rssi_sum,
                rssi_count,
                rssi_min,
                rssi_max,
            ) = row[9:17]
        else:
            snr_sum = snr_count = snr_min = snr_max = None
            rssi_sum = rssi_count = rssi_min = rssi_max = None
        portnums = _safe_json_loads(portnums_json, [])
        if not isinstance(portnums, list):
            portnums = []
        out.append(
            {
                "from": str(from_id),
                "to": str(to_id),
                "count": int(seen_count),
                "first_rx_time": _to_int(first_seen_unix),
                "last_rx_time": _to_int(last_seen_unix),
                "portnums": [str(p) for p in portnums if p is not None],
                "last_hops": _to_int(last_hops),
                "hops_sum": _to_int(hops_sum) or 0,
                "hops_count": _to_int(hops_count) or 0,
                "snr_sum": _to_float(snr_sum) or 0.0,
                "snr_count": _to_int(snr_count) or 0,
                "snr_min": _to_float(snr_min),
                "snr_max": _to_float(snr_max),
                "rssi_sum": _to_float(rssi_sum) or 0.0,
                "rssi_count": _to_int(rssi_count) or 0,
                "rssi_min": _to_float(rssi_min),
                "rssi_max": _to_float(rssi_max),
            }
        )
    return out
