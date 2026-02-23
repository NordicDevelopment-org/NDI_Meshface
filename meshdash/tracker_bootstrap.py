from typing import Any, Callable, Dict, Iterable, Tuple


def load_tracker_history_bootstrap(
    history_store: Any,
    *,
    packet_limit: int,
    build_historical_edges_fn: Callable[[Iterable[Dict[str, Any]]], Dict[Tuple[str, str], Dict[str, Any]]],
) -> Dict[str, Any]:
    recent_packets = list(history_store.load_recent_packets(packet_limit))
    recent_chat = list(history_store.load_recent_chat(packet_limit))
    historical_edges = build_historical_edges_fn(history_store.load_connections())
    return {
        "recent_packets": recent_packets,
        "recent_chat": recent_chat,
        "historical_edges": historical_edges,
    }
