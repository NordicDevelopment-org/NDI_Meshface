from collections.abc import Iterable

from .runtime_types import GetNodeIdFromNumFn


def _normalize_packet_node_id(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    if lowered in ("^all", "all", "broadcast", "!ffffffff", "ffffffff", "0xffffffff", "4294967295"):
        return "^all"
    if text.startswith("!") and len(text) == 9:
        raw = text[1:]
        if all(ch in "0123456789abcdefABCDEF" for ch in raw):
            return f"!{raw.lower()}"
    if len(text) == 8 and all(ch in "0123456789abcdefABCDEF" for ch in text):
        return f"!{text.lower()}"
    return text


def _resolve_node_id(value: object, interface: object, get_node_id_from_num_fn: GetNodeIdFromNumFn) -> str:
    if isinstance(value, bool):
        return ""
    if isinstance(value, int):
        return _normalize_packet_node_id(get_node_id_from_num_fn(interface, value))
    if isinstance(value, float) and value.is_integer():
        return _normalize_packet_node_id(get_node_id_from_num_fn(interface, int(value)))
    if isinstance(value, str):
        text = value.strip()
        if text and text.isdigit():
            return _normalize_packet_node_id(get_node_id_from_num_fn(interface, int(text)))
    normalized = _normalize_packet_node_id(value)
    if normalized:
        return normalized
    try:
        numeric = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return ""
    return _normalize_packet_node_id(get_node_id_from_num_fn(interface, numeric))


def _neighbor_payload(decoded: object) -> dict[str, object] | None:
    if not isinstance(decoded, dict):
        return None
    for key in ("neighborinfo", "neighbor_info", "neighborInfo"):
        value = decoded.get(key)
        if isinstance(value, dict):
            return value
    payload = decoded.get("payload")
    if isinstance(payload, dict):
        for key in ("neighborinfo", "neighbor_info", "neighborInfo"):
            value = payload.get(key)
            if isinstance(value, dict):
                return value
        return payload
    return None


def extract_neighbor_info_edges(
    decoded: object,
    *,
    interface: object,
    get_node_id_from_num_fn: GetNodeIdFromNumFn,
) -> list[dict[str, object]]:
    payload = _neighbor_payload(decoded)
    if not isinstance(payload, dict):
        return []
    source_id = _resolve_node_id(payload.get("node_id") or payload.get("nodeId"), interface, get_node_id_from_num_fn)
    if not source_id or source_id == "^all":
        return []
    neighbors = payload.get("neighbors")
    if not isinstance(neighbors, Iterable) or isinstance(neighbors, (str, bytes, dict)):
        return []
    rows: list[dict[str, object]] = []
    for entry in neighbors:
        if not isinstance(entry, dict):
            continue
        neighbor_id = _resolve_node_id(
            entry.get("node_id") or entry.get("nodeId"),
            interface,
            get_node_id_from_num_fn,
        )
        if not neighbor_id or neighbor_id == "^all" or neighbor_id == source_id:
            continue
        try:
            last_rx_time = int(entry.get("last_rx_time") or entry.get("lastRxTime") or 0)
        except (TypeError, ValueError):
            last_rx_time = 0
        try:
            snr = float(entry.get("snr"))
        except (TypeError, ValueError):
            snr = None
        rows.append(
            {
                "from_id": source_id,
                "to_id": neighbor_id,
                "rx_time": last_rx_time if last_rx_time > 0 else None,
                "rx_snr": snr,
            }
        )
    return rows
