from collections import Counter, deque
from dataclasses import dataclass
from typing import Any, Dict, Tuple

from .tracker_bootstrap import TrackerHistoryBootstrap


@dataclass
class TrackerBuffers:
    edges: Dict[Any, Dict[str, Any]]
    historical_edges: Dict[Any, Dict[str, Any]]
    port_counts: Any
    recent_packets: Any
    recent_chat: Any


def initialize_tracker_buffers(packet_limit: int) -> TrackerBuffers:
    return TrackerBuffers(
        edges={},
        historical_edges={},
        port_counts=Counter(),
        recent_packets=deque(maxlen=packet_limit),
        recent_chat=deque(maxlen=packet_limit),
    )


def apply_tracker_history_bootstrap(
    *,
    history_store: Any,
    packet_limit: int,
    recent_packets: Any,
    recent_chat: Any,
    load_tracker_history_bootstrap_fn: Any,
    build_historical_edges_fn: Any,
) -> Dict[Tuple[str, str], Dict[str, Any]]:
    if history_store is None:
        return {}
    bootstrap: TrackerHistoryBootstrap = load_tracker_history_bootstrap_fn(
        history_store,
        packet_limit=packet_limit,
        build_historical_edges_fn=build_historical_edges_fn,
    )
    recent_packets.extend(bootstrap.recent_packets)
    recent_chat.extend(bootstrap.recent_chat)
    return bootstrap.historical_edges
