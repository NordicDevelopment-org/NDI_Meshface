from typing import Any

from .nodes import safe_nodes_items as _safe_nodes_items


def seed_tracker_from_node_db(
    tracker: Any,
    iface: Any,
    *,
    safe_nodes_items_fn=_safe_nodes_items,
) -> None:
    for _num, node in safe_nodes_items_fn(iface, retries=3, sleep_seconds=0.01):
        if not isinstance(node, dict):
            continue
        last_packet = node.get("lastReceived")
        if isinstance(last_packet, dict):
            tracker.seed_packet(last_packet, iface)
