import time
from collections.abc import Mapping
from typing import Callable, Optional

from .revision import RevisionInfo
from .tracker_snapshot_contracts import TrackerSnapshot

from .helpers import disk_space_info
from .helpers import to_int
from .helpers_node_names import prefer_stable_node_name as _prefer_stable_node_name_helper


def _clean_summary_node_id(value: object) -> str:
    clean = str(value or "").strip()
    if not clean or clean in {"Unknown", "n/a", "^all"}:
        return ""
    return clean


def apply_node_saved_counts(
    rows: list[dict[str, object]],
    node_saved_counts: dict[str, dict[str, object]],
) -> None:
    for row in rows:
        stats = node_saved_counts.get(str(row.get("id") or ""), {})
        row["saved_packets"] = int(stats.get("saved_packets") or 0)
        row["saved_points"] = int(stats.get("saved_points") or 0)
        row["saved_last_seen"] = stats.get("saved_last_seen")


def apply_node_position_counts(
    rows: list[dict[str, object]],
    node_position_counts: Mapping[str, Mapping[str, object]],
) -> None:
    for row in rows:
        stats = node_position_counts.get(str(row.get("id") or ""), {})
        position_points = int(stats.get("position_points") or stats.get("location_points") or 0)
        row["position_points"] = position_points
        row["position_last_seen_unix"] = stats.get("position_last_seen_unix")
        row["position_last_seen"] = stats.get("position_last_seen")


def apply_node_link_counts(
    rows: list[dict[str, object]],
    edges: list[dict[str, object]],
) -> None:
    peers_by_node: dict[str, set[str]] = {}
    packets_by_node: dict[str, int] = {}
    for edge in edges:
        if not isinstance(edge, Mapping):
            continue
        from_id = _clean_summary_node_id(edge.get("from") or edge.get("a"))
        to_id = _clean_summary_node_id(edge.get("to") or edge.get("b"))
        if not from_id or not to_id or from_id == to_id:
            continue
        packet_count = to_int(
            edge.get("lifetime_count")
            if edge.get("lifetime_count") is not None
            else edge.get("session_count")
        )
        if packet_count is None:
            packet_count = to_int(edge.get("count")) or 0
        for node_id, peer_id in ((from_id, to_id), (to_id, from_id)):
            peers_by_node.setdefault(node_id, set()).add(peer_id)
            packets_by_node[node_id] = packets_by_node.get(node_id, 0) + max(0, int(packet_count))
    for row in rows:
        node_id = str(row.get("id") or "").strip()
        row["link_count"] = len(peers_by_node.get(node_id, set()))
        row["link_packet_count"] = int(packets_by_node.get(node_id, 0))


def apply_node_historical_names(
    rows: list[dict[str, object]],
    history_caps: Mapping[str, Mapping[str, object]],
) -> None:
    for row in rows:
        node_id = str(row.get("id") or "").strip()
        if not node_id:
            continue
        caps = history_caps.get(node_id)
        if not isinstance(caps, Mapping):
            continue
        next_long_name = _prefer_stable_node_name_helper(
            row.get("long_name"),
            caps.get("last_long_name"),
            node_id,
        )
        next_short_name = _prefer_stable_node_name_helper(
            row.get("short_name"),
            caps.get("last_short_name"),
            node_id,
        )
        if next_long_name:
            row["long_name"] = next_long_name
        if next_short_name:
            row["short_name"] = next_short_name
        first_seen_unix = caps.get("first_seen_unix")
        if first_seen_unix is not None:
            row["first_seen_unix"] = first_seen_unix
        first_seen = caps.get("first_seen")
        if first_seen is not None:
            row["first_seen"] = first_seen


def collect_local_state_safe(
    iface: object,
    *,
    collect_local_state_fn: Callable[[object], dict[str, object]],
) -> tuple[dict[str, object], Optional[str]]:
    try:
        return collect_local_state_fn(iface), None
    except Exception as exc:
        return {}, str(exc)


def modem_preset_from_local_state(local_state: dict[str, object]) -> Optional[str]:
    try:
        return (local_state.get("local_config") or {}).get("lora", {}).get("modem_preset")
    except Exception:
        return None


def build_summary_payload(
    *,
    target: str,
    started_at: float,
    node_rows: list[dict[str, object]],
    nodes_with_position: int,
    tracker_data: TrackerSnapshot,
    storage_probe_path: Optional[str],
    revision_info: RevisionInfo,
    modem_preset: Optional[str],
    now_ts_fn: Callable[[], float] = time.time,
    disk_space_info_fn: Callable[[Optional[str]], dict[str, object]] = disk_space_info,
) -> dict[str, object]:
    tracker_snapshot = tracker_data
    return {
        "target": target,
        "uptime_seconds": int(max(0, now_ts_fn() - started_at)),
        "node_count": len(node_rows),
        "nodes_with_position": nodes_with_position,
        "live_packet_count": tracker_snapshot.live_packet_count,
        "edge_count": len(tracker_snapshot.edges),
        "real_edge_count": tracker_snapshot.real_edge_count,
        "recent_packet_buffer": len(tracker_snapshot.recent_packets),
        "modem_preset": modem_preset,
        "disk": disk_space_info_fn(storage_probe_path),
        "revision": revision_info.as_dict(),
    }
