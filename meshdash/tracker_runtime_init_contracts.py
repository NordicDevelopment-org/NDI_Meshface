from typing import Any, Protocol

from .runtime_types import (
    ExtractDeliveryUpdateFn,
    GetTimeoutSecondsFn,
    NowUnixFn,
    ParseUtcTextToUnixFn,
    SetDeliveryStateFn,
    ToIntFn,
    TrackerEdgeMap,
    UtcNowFn,
)
from .tracker_bootstrap_contracts import BuildHistoricalEdgesFn, TrackerBootstrapHistoryStore
from .tracker_bootstrap import TrackerHistoryBootstrap
from .tracker_callbacks import TrackerDeliveryCallbacks
from .tracker_snapshot_build_contracts import ExpirePendingDeliveriesFn, TrackerHistoryStore


class TrackerBuffersLike(Protocol):
    edges: TrackerEdgeMap
    historical_edges: TrackerEdgeMap
    port_counts: Any
    recent_packets: Any
    recent_chat: Any


class TrackerInitRuntimeState(Protocol):
    _history_store: "TrackerRuntimeHistoryStore | None"
    _chat_delivery_timeout_seconds: int
    live_packet_count: int
    edges: TrackerEdgeMap
    _historical_edges: TrackerEdgeMap
    port_counts: Any
    recent_packets: Any
    recent_chat: Any
    _set_delivery_state_fn: SetDeliveryStateFn
    _extract_delivery_update_fn: ExtractDeliveryUpdateFn
    _expire_pending_deliveries_fn: ExpirePendingDeliveriesFn


class InitializeTrackerBuffersFn(Protocol):
    def __call__(self, packet_limit: int) -> TrackerBuffersLike:
        ...


class BuildTrackerDeliveryCallbacksFn(Protocol):
    def __call__(
        self,
        recent_chat: Any,
        *,
        get_timeout_seconds_fn: GetTimeoutSecondsFn,
        to_int_fn: ToIntFn,
        parse_utc_text_to_unix_fn: ParseUtcTextToUnixFn,
        utc_now_fn: UtcNowFn,
        now_unix_fn: NowUnixFn,
    ) -> TrackerDeliveryCallbacks:
        ...


class TrackerRuntimeHistoryStore(TrackerHistoryStore, TrackerBootstrapHistoryStore, Protocol):
    pass


class LoadTrackerHistoryBootstrapFn(Protocol):
    def __call__(
        self,
        history_store: TrackerBootstrapHistoryStore,
        *,
        packet_limit: int,
        build_historical_edges_fn: BuildHistoricalEdgesFn,
    ) -> TrackerHistoryBootstrap:
        ...


class ApplyTrackerHistoryBootstrapFn(Protocol):
    def __call__(
        self,
        *,
        history_store: TrackerBootstrapHistoryStore | None,
        packet_limit: int,
        recent_packets: Any,
        recent_chat: Any,
        load_tracker_history_bootstrap_fn: LoadTrackerHistoryBootstrapFn,
        build_historical_edges_fn: BuildHistoricalEdgesFn,
    ) -> TrackerEdgeMap:
        ...
