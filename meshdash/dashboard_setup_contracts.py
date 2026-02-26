from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from .dashboard_args_contracts import DashboardArgs


class HistoryStoreLike(Protocol):
    def close(self) -> None:
        ...


class HistoryStoreFactory(Protocol):
    def __call__(
        self,
        *,
        db_path: str,
        max_rows: int,
        retention_days: int,
        event_max_rows: int,
        event_retention_days: int,
        rollup_retention_days: int,
    ) -> HistoryStoreLike:
        ...


class DashboardTrackerLike(Protocol):
    def on_receive(self, packet: object, interface: object) -> object:
        ...

    def has_recent_packets(self) -> bool:
        ...


class DashboardTrackerFactory(Protocol):
    def __call__(
        self,
        *,
        packet_limit: int,
        history_store: HistoryStoreLike | None,
    ) -> DashboardTrackerLike:
        ...


class PrintLineFn(Protocol):
    def __call__(self, text: str) -> None:
        ...


class SeedTrackerBootstrapFn(Protocol):
    def __call__(self, tracker: DashboardTrackerLike, iface: object) -> None:
        ...


class OpenOptionalHistoryStoreFn(Protocol):
    def __call__(
        self,
        args: "DashboardArgs",
        *,
        history_store_cls: HistoryStoreFactory,
        history_db_path: str,
    ) -> HistoryStoreLike | None:
        ...


class SeedTrackerIfEmptyFn(Protocol):
    def __call__(
        self,
        tracker: DashboardTrackerLike,
        iface: object,
        *,
        seed_tracker_fn: SeedTrackerBootstrapFn,
    ) -> None:
        ...
