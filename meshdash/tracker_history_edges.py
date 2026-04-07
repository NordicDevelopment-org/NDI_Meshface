from collections.abc import Iterable

from .tracker_snapshot_build_contracts import EdgeKey, EdgeRow


def _to_float(value: object) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed:
        return None
    return parsed


def build_historical_edges(
    connection_rows: Iterable[EdgeRow],
) -> dict[EdgeKey, EdgeRow]:
    out: dict[EdgeKey, EdgeRow] = {}
    for edge in connection_rows:
        from_id = str(edge["from"])
        to_id = str(edge["to"])
        key = (from_id, to_id)
        out[key] = {
            "from": from_id,
            "to": to_id,
            "count": int(edge["count"]),
            "first_rx_time": edge.get("first_rx_time"),
            "last_rx_time": edge.get("last_rx_time"),
            "portnums": set(edge.get("portnums") or []),
            "last_hops": edge.get("last_hops"),
            "hops_sum": int(edge.get("hops_sum") or 0),
            "hops_count": int(edge.get("hops_count") or 0),
            "snr_sum": _to_float(edge.get("snr_sum")) or 0.0,
            "snr_count": int(edge.get("snr_count") or 0),
            "snr_min": _to_float(edge.get("snr_min")),
            "snr_max": _to_float(edge.get("snr_max")),
            "rssi_sum": _to_float(edge.get("rssi_sum")) or 0.0,
            "rssi_count": int(edge.get("rssi_count") or 0),
            "rssi_min": _to_float(edge.get("rssi_min")),
            "rssi_max": _to_float(edge.get("rssi_max")),
        }
    return out
