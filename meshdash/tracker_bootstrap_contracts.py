from typing import Any, Iterable, Protocol

from .runtime_types import TrackerEdgeMap


class TrackerBootstrapHistoryStore(Protocol):
    def load_recent_packets(self, limit: int) -> Iterable[dict[str, Any]]:
        ...

    def load_recent_chat(self, limit: int) -> Iterable[dict[str, Any]]:
        ...

    def load_connections(self) -> Iterable[dict[str, Any]]:
        ...


class BuildHistoricalEdgesFn(Protocol):
    def __call__(self, connection_rows: Iterable[dict[str, Any]]) -> TrackerEdgeMap:
        ...
