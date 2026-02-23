import time
from typing import Any, Dict, Optional

from .helpers import (
    disk_space_info,
    redact_secrets,
    to_jsonable,
)
from .nodes import utc_now
from .state_nodes import (
    collect_local_state as _collect_local_state_helper,
    collect_nodes as _collect_nodes_helper,
)


def collect_nodes(iface: Any) -> Dict[str, Any]:
    return _collect_nodes_helper(iface)


def collect_local_state(iface: Any) -> Dict[str, Any]:
    return _collect_local_state_helper(iface)


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
