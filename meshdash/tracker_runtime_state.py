from typing import Any, Dict

from .helpers import (
    format_epoch as _format_epoch,
)
from .tracker_snapshot import (
    build_edge_snapshot_rows as _build_edge_snapshot_rows_helper,
    build_tracker_snapshot_payload as _build_tracker_snapshot_payload_helper,
)


def load_tracker_node_saved_counts(history_store: Any) -> Dict[str, Dict[str, Any]]:
    if history_store is None:
        return {}
    return history_store.load_node_saved_counts()


def load_tracker_node_capabilities(history_store: Any) -> Dict[str, Dict[str, Any]]:
    if history_store is None:
        return {}
    return history_store.load_node_capabilities()


def build_tracker_snapshot(
    *,
    nodes_by_id: Dict[str, Dict[str, Any]],
    expire_pending_deliveries_fn: Any,
    session_edges: Dict[Any, Dict[str, Any]],
    historical_edges: Dict[Any, Dict[str, Any]],
    port_counts: Any,
    recent_packets: Any,
    recent_chat: Any,
    live_packet_count: int,
    min_real_link_count: int,
    format_epoch_fn: Any,
    build_edge_snapshot_rows_fn: Any,
    build_tracker_snapshot_payload_fn: Any,
) -> Dict[str, Any]:
    expire_pending_deliveries_fn()
    return build_tracker_snapshot_payload_fn(
        session_edges=session_edges,
        historical_edges=historical_edges,
        nodes_by_id=nodes_by_id,
        port_counts=port_counts,
        recent_packets=recent_packets,
        recent_chat=recent_chat,
        live_packet_count=live_packet_count,
        min_real_link_count=min_real_link_count,
        format_epoch_fn=format_epoch_fn,
        build_edge_snapshot_rows_fn=build_edge_snapshot_rows_fn,
    )


def load_tracker_node_saved_counts_for_tracker(tracker: Any) -> Dict[str, Dict[str, Any]]:
    return load_tracker_node_saved_counts(tracker._history_store)


def load_tracker_node_capabilities_for_tracker(tracker: Any) -> Dict[str, Dict[str, Any]]:
    return load_tracker_node_capabilities(tracker._history_store)


def build_tracker_snapshot_for_tracker(
    tracker: Any,
    *,
    nodes_by_id: Dict[str, Dict[str, Any]],
    min_real_link_count: int,
    format_epoch_fn: Any = _format_epoch,
    build_edge_snapshot_rows_fn: Any = _build_edge_snapshot_rows_helper,
    build_tracker_snapshot_payload_fn: Any = _build_tracker_snapshot_payload_helper,
) -> Dict[str, Any]:
    return build_tracker_snapshot(
        nodes_by_id=nodes_by_id,
        expire_pending_deliveries_fn=tracker._expire_pending_deliveries_fn,
        session_edges=tracker.edges,
        historical_edges=tracker._historical_edges,
        port_counts=tracker.port_counts,
        recent_packets=tracker.recent_packets,
        recent_chat=tracker.recent_chat,
        live_packet_count=tracker.live_packet_count,
        min_real_link_count=min_real_link_count,
        format_epoch_fn=format_epoch_fn,
        build_edge_snapshot_rows_fn=build_edge_snapshot_rows_fn,
        build_tracker_snapshot_payload_fn=build_tracker_snapshot_payload_fn,
    )
