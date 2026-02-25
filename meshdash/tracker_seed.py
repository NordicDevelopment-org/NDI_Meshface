from .nodes import safe_nodes_items as _safe_nodes_items
from .tracker_seed_contracts import SafeNodesItemsFn, TrackerSeedTarget


def seed_tracker_from_node_db(
    tracker: TrackerSeedTarget,
    iface: object,
    *,
    safe_nodes_items_fn: SafeNodesItemsFn = _safe_nodes_items,
) -> None:
    for _num, node in safe_nodes_items_fn(iface, retries=3, sleep_seconds=0.01):
        if not isinstance(node, dict):
            continue
        last_packet = node.get("lastReceived")
        if isinstance(last_packet, dict):
            tracker.seed_packet(last_packet, iface)
