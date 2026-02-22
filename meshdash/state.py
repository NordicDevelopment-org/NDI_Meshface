import time
from typing import Any, Dict, Optional

from .helpers import (
    disk_space_info,
    format_epoch,
    redact_secrets,
    to_int,
    to_jsonable,
)
from .nodes import extract_position, safe_nodes_items, utc_now


def collect_nodes(iface: Any) -> Dict[str, Any]:
    rows: list[Dict[str, Any]] = []
    full_nodes: list[Dict[str, Any]] = []
    nodes_by_id: Dict[str, Dict[str, Any]] = {}

    for node_num, raw_info in safe_nodes_items(iface):
        if not isinstance(raw_info, dict):
            continue

        info = to_jsonable(raw_info)
        if not isinstance(info, dict):
            continue

        node_num_int = to_int(info.get("num", node_num))
        user = info.get("user", {}) if isinstance(info.get("user"), dict) else {}
        node_id = user.get("id")
        if not node_id and node_num_int is not None:
            node_id = f"!{node_num_int:08x}"

        if not node_id:
            continue

        metrics = info.get("deviceMetrics", {}) if isinstance(info.get("deviceMetrics"), dict) else {}
        position = extract_position(info)
        last_heard_epoch = to_int(info.get("lastHeard")) or 0

        row = {
            "id": str(node_id),
            "num": node_num_int,
            "short_name": user.get("shortName"),
            "long_name": user.get("longName"),
            "hardware_model": user.get("hwModel"),
            "role": user.get("role"),
            "is_licensed": user.get("isLicensed"),
            "last_heard": format_epoch(last_heard_epoch),
            "last_heard_epoch": last_heard_epoch,
            "last_heard_unix": last_heard_epoch,
            "snr": info.get("snr"),
            "hops_away": info.get("hopsAway"),
            "battery_level": metrics.get("batteryLevel"),
            "voltage": metrics.get("voltage"),
            "channel_utilization": metrics.get("channelUtilization"),
            "air_util_tx": metrics.get("airUtilTx"),
            "lat": position[0] if position else None,
            "lon": position[1] if position else None,
        }
        rows.append(row)
        nodes_by_id[str(node_id)] = row
        full_nodes.append(
            {
                "id": str(node_id),
                "num": node_num_int,
                "info": info,
            }
        )

    rows.sort(key=lambda item: item.get("last_heard_epoch", 0), reverse=True)
    for row in rows:
        row.pop("last_heard_epoch", None)

    full_nodes.sort(key=lambda item: item.get("num") or 0)
    nodes_with_position = sum(
        1 for node in rows if node.get("lat") is not None and node.get("lon") is not None
    )

    return {
        "rows": rows,
        "full": full_nodes,
        "by_id": nodes_by_id,
        "with_position_count": nodes_with_position,
    }


def collect_local_state(iface: Any) -> Dict[str, Any]:
    local = getattr(iface, "localNode", None)
    if local is None:
        local = iface.getNode("^local")

    state: Dict[str, Any] = {}
    state["local_config"] = to_jsonable(getattr(local, "localConfig", None))
    state["module_config"] = to_jsonable(getattr(local, "moduleConfig", None))
    channels = getattr(local, "channels", None)
    if channels is None:
        state["channels"] = []
    else:
        state["channels"] = [to_jsonable(channel) for channel in channels]
    return state


def build_state(
    iface: Any,
    tracker: Any,
    started_at: float,
    target: str,
    show_secrets: bool,
    storage_probe_path: Optional[str],
    revision_info: Dict[str, str],
    sensitive_field_names: set[str],
) -> Dict[str, Any]:
    nodes = collect_nodes(iface)
    tracker_data = tracker.snapshot(nodes["by_id"])
    node_saved_counts = tracker.load_node_saved_counts()
    node_capabilities = tracker.load_node_capabilities()
    for row in nodes["rows"]:
        stats = node_saved_counts.get(str(row.get("id") or ""), {})
        row["saved_packets"] = int(stats.get("saved_packets") or 0)
        row["saved_points"] = int(stats.get("saved_points") or 0)
        row["saved_last_seen"] = stats.get("saved_last_seen")

    my_info = to_jsonable(getattr(iface, "myInfo", None))
    metadata = to_jsonable(getattr(iface, "metadata", None))

    local_state: Dict[str, Any]
    local_error: Optional[str] = None
    try:
        local_state = collect_local_state(iface)
    except Exception as exc:
        local_state = {}
        local_error = str(exc)

    modem_preset = None
    try:
        modem_preset = (
            (local_state.get("local_config") or {})
            .get("lora", {})
            .get("modem_preset")
        )
    except Exception:
        modem_preset = None

    state = {
        "generated_at": utc_now(),
        "summary": {
            "target": target,
            "uptime_seconds": int(max(0, time.time() - started_at)),
            "node_count": len(nodes["rows"]),
            "nodes_with_position": nodes["with_position_count"],
            "live_packet_count": tracker_data["live_packet_count"],
            "edge_count": len(tracker_data["edges"]),
            "real_edge_count": tracker_data["real_edge_count"],
            "recent_packet_buffer": len(tracker_data["recent_packets"]),
            "modem_preset": modem_preset,
            "disk": disk_space_info(storage_probe_path),
            "revision": revision_info,
        },
        "my_info": my_info,
        "metadata": metadata,
        "local_state": local_state,
        "local_state_error": local_error,
        "nodes": nodes["rows"],
        "history_caps": node_capabilities,
        "nodes_full": nodes["full"],
        "traffic": {
            "edges": tracker_data["edges"],
            "port_counts": tracker_data["port_counts"],
            "recent_packets": tracker_data["recent_packets"],
            "recent_chat": tracker_data["recent_chat"],
        },
    }

    if not show_secrets:
        state = redact_secrets(state, sensitive_field_names)

    return state
