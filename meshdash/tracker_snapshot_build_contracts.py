from typing import Any, Protocol

from .runtime_types import FormatEpochFn
from .tracker_snapshot_contracts import TrackerSnapshot


class TrackerHistoryStore(Protocol):
    def load_node_saved_counts(self) -> dict[str, dict[str, Any]]:
        ...

    def load_node_capabilities(self) -> dict[str, dict[str, Any]]:
        ...


class ExpirePendingDeliveriesFn(Protocol):
    def __call__(self) -> None:
        ...


class BuildEdgeSnapshotRowsFn(Protocol):
    def __call__(
        self,
        *,
        session_edges: dict[Any, dict[str, Any]],
        historical_edges: dict[Any, dict[str, Any]],
        nodes_by_id: dict[str, dict[str, Any]],
        min_real_link_count: int,
        format_epoch_fn: FormatEpochFn,
    ) -> tuple[list[dict[str, Any]], int]:
        ...


class BuildTrackerSnapshotPayloadTypedFn(Protocol):
    def __call__(
        self,
        *,
        session_edges: dict[Any, dict[str, Any]],
        historical_edges: dict[Any, dict[str, Any]],
        nodes_by_id: dict[str, dict[str, Any]],
        port_counts: Any,
        recent_packets: Any,
        recent_chat: Any,
        live_packet_count: int,
        min_real_link_count: int,
        format_epoch_fn: FormatEpochFn,
        build_edge_snapshot_rows_fn: BuildEdgeSnapshotRowsFn,
    ) -> TrackerSnapshot:
        ...


class BuildTrackerSnapshotPayloadFn(Protocol):
    def __call__(
        self,
        *,
        session_edges: dict[Any, dict[str, Any]],
        historical_edges: dict[Any, dict[str, Any]],
        nodes_by_id: dict[str, dict[str, Any]],
        port_counts: Any,
        recent_packets: Any,
        recent_chat: Any,
        live_packet_count: int,
        min_real_link_count: int,
        format_epoch_fn: FormatEpochFn,
        build_edge_snapshot_rows_fn: BuildEdgeSnapshotRowsFn,
    ) -> dict[str, Any]:
        ...
