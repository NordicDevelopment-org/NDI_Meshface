from typing import Optional

from .tracker_snapshot_build_contracts import EdgeKey, EdgeRow


def _to_metric_value(value: object) -> float | None:
    try:
        metric = float(value)
    except (TypeError, ValueError):
        return None
    if metric != metric:
        return None
    return metric


def _merge_signal_metric(edge: EdgeRow, prefix: str, value: object) -> None:
    metric = _to_metric_value(value)
    if metric is None:
        return
    sum_key = f"{prefix}_sum"
    count_key = f"{prefix}_count"
    min_key = f"{prefix}_min"
    max_key = f"{prefix}_max"
    edge[sum_key] = float(edge.get(sum_key) or 0.0) + metric
    edge[count_key] = int(edge.get(count_key) or 0) + 1
    current_min = _to_metric_value(edge.get(min_key))
    current_max = _to_metric_value(edge.get(max_key))
    edge[min_key] = metric if current_min is None else min(current_min, metric)
    edge[max_key] = metric if current_max is None else max(current_max, metric)


def _new_edge(from_id: str, to_id: str) -> EdgeRow:
    return {
        "from": from_id,
        "to": to_id,
        "count": 0,
        "first_rx_time": None,
        "last_rx_time": None,
        "portnums": set(),
        "last_hops": None,
        "hops_sum": 0,
        "hops_count": 0,
        "snr_sum": 0.0,
        "snr_count": 0,
        "snr_min": None,
        "snr_max": None,
        "rssi_sum": 0.0,
        "rssi_count": 0,
        "rssi_min": None,
        "rssi_max": None,
    }


def is_direct_link(from_id: object, to_id: object) -> bool:
    return (
        bool(from_id)
        and bool(to_id)
        and from_id not in ("Unknown",)
        and to_id not in ("^all", "Unknown")
        and str(from_id) != str(to_id)
    )


def record_direct_edge_observation(
    *,
    session_edges: dict[EdgeKey, EdgeRow],
    historical_edges: dict[EdgeKey, EdgeRow],
    from_id: object,
    to_id: object,
    rx_time: Optional[int],
    portnum: Optional[object],
    hops: Optional[int],
    rx_snr: Optional[object],
    rx_rssi: Optional[object],
    include_live_count: bool,
) -> Optional[EdgeKey]:
    if not is_direct_link(from_id, to_id):
        return None

    clean_from = str(from_id)
    clean_to = str(to_id)
    key = (clean_from, clean_to)

    edge = session_edges.setdefault(key, _new_edge(clean_from, clean_to))
    edge["count"] += 1
    if rx_time is not None and (edge["first_rx_time"] is None or rx_time < edge["first_rx_time"]):
        edge["first_rx_time"] = rx_time
    if rx_time is not None and (edge["last_rx_time"] is None or rx_time > edge["last_rx_time"]):
        edge["last_rx_time"] = rx_time
    if portnum is not None:
        edge["portnums"].add(str(portnum))
    if hops is not None:
        edge["last_hops"] = hops
        edge["hops_sum"] += hops
        edge["hops_count"] += 1
    _merge_signal_metric(edge, "snr", rx_snr)
    _merge_signal_metric(edge, "rssi", rx_rssi)

    if include_live_count:
        hist = historical_edges.setdefault(key, _new_edge(clean_from, clean_to))
        hist["count"] += 1
        if rx_time is not None and (hist["first_rx_time"] is None or rx_time < hist["first_rx_time"]):
            hist["first_rx_time"] = rx_time
        if rx_time is not None and (hist["last_rx_time"] is None or rx_time > hist["last_rx_time"]):
            hist["last_rx_time"] = rx_time
        if portnum is not None:
            hist["portnums"].add(str(portnum))
        if hops is not None:
            hist["last_hops"] = hops
            hist["hops_sum"] += hops
            hist["hops_count"] += 1
        _merge_signal_metric(hist, "snr", rx_snr)
        _merge_signal_metric(hist, "rssi", rx_rssi)

    return key
