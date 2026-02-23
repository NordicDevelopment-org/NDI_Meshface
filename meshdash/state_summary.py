import time
from typing import Any, Callable, Dict, Optional

from .helpers import disk_space_info


def apply_node_saved_counts(
    rows: list[Dict[str, Any]],
    node_saved_counts: Dict[str, Dict[str, Any]],
) -> None:
    for row in rows:
        stats = node_saved_counts.get(str(row.get("id") or ""), {})
        row["saved_packets"] = int(stats.get("saved_packets") or 0)
        row["saved_points"] = int(stats.get("saved_points") or 0)
        row["saved_last_seen"] = stats.get("saved_last_seen")


def collect_local_state_safe(
    iface: Any,
    *,
    collect_local_state_fn: Callable[[Any], Dict[str, Any]],
) -> tuple[Dict[str, Any], Optional[str]]:
    try:
        return collect_local_state_fn(iface), None
    except Exception as exc:
        return {}, str(exc)


def modem_preset_from_local_state(local_state: Dict[str, Any]) -> Optional[str]:
    try:
        return (local_state.get("local_config") or {}).get("lora", {}).get("modem_preset")
    except Exception:
        return None


def build_summary_payload(
    *,
    target: str,
    started_at: float,
    node_rows: list[Dict[str, Any]],
    nodes_with_position: int,
    tracker_data: Dict[str, Any],
    storage_probe_path: Optional[str],
    revision_info: Dict[str, str],
    modem_preset: Optional[str],
    now_ts_fn: Callable[[], float] = time.time,
    disk_space_info_fn: Callable[[Optional[str]], Dict[str, Any]] = disk_space_info,
) -> Dict[str, Any]:
    return {
        "target": target,
        "uptime_seconds": int(max(0, now_ts_fn() - started_at)),
        "node_count": len(node_rows),
        "nodes_with_position": nodes_with_position,
        "live_packet_count": tracker_data["live_packet_count"],
        "edge_count": len(tracker_data["edges"]),
        "real_edge_count": tracker_data["real_edge_count"],
        "recent_packet_buffer": len(tracker_data["recent_packets"]),
        "modem_preset": modem_preset,
        "disk": disk_space_info_fn(storage_probe_path),
        "revision": revision_info,
    }
