from typing import Any, Callable, Protocol

HistoryPayload = dict[str, Any]
HistoryListPayload = list[HistoryPayload]
NodeCapabilityMap = dict[str, HistoryPayload]


class FetchRowsWithLimitFn(Protocol):
    def __call__(self, conn: Any, *, limit: int) -> Any: ...


class FetchRowsFn(Protocol):
    def __call__(self, conn: Any) -> Any: ...


class DecodeRowsListFn(Protocol):
    def __call__(self, rows: Any) -> HistoryListPayload: ...


class DecodeNodeCapabilityMapFn(Protocol):
    def __call__(self, rows: Any) -> NodeCapabilityMap: ...


class FetchNodeHistoryRowsFn(Protocol):
    def __call__(
        self,
        conn: Any,
        *,
        node_id: str,
        cutoff: int,
        limit: int,
    ) -> tuple[Any, Any]: ...


class BuildNodeHistoryPayloadFn(Protocol):
    def __call__(
        self,
        *,
        node_id: str,
        window_hours: int,
        metric_rows: Any,
        position_rows: Any,
    ) -> HistoryPayload: ...


class FetchOnlineActivityRowsFn(Protocol):
    def __call__(
        self,
        conn: Any,
        *,
        cutoff: int,
    ) -> tuple[Any, int]: ...


class BuildOnlineActivityPayloadFn(Protocol):
    def __call__(
        self,
        *,
        window_hours: int,
        hour_rows: Any,
        distinct_nodes: int,
        timezone_label: str,
    ) -> HistoryPayload: ...


TimezoneLabelFn = Callable[[], str]
