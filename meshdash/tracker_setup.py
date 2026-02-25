from collections import Counter, deque
from dataclasses import dataclass
from typing import Any, Dict, MutableSequence

from .tracker_bootstrap import TrackerHistoryBootstrap
from .tracker_bootstrap_contracts import TrackerBootstrapHistoryStore
from .tracker_runtime_init_contracts import BuildHistoricalEdgesFn, LoadTrackerHistoryBootstrapFn


@dataclass
class TrackerBuffers:
    edges: Dict[Any, Dict[str, Any]]
    historical_edges: Dict[Any, Dict[str, Any]]
    port_counts: Counter[str]
    recent_packets: deque[dict[str, Any]]
    recent_chat: deque[dict[str, Any]]


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
    history_store: TrackerBootstrapHistoryStore | None,
    packet_limit: int,
    recent_packets: MutableSequence[dict[str, Any]],
    recent_chat: MutableSequence[dict[str, Any]],
    load_tracker_history_bootstrap_fn: LoadTrackerHistoryBootstrapFn,
    build_historical_edges_fn: BuildHistoricalEdgesFn,
) -> Dict[Any, Dict[str, Any]]:
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
