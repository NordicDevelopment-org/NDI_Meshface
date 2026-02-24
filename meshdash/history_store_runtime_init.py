import threading
from typing import Any, Callable

from .history_store_connection import (
    open_and_initialize_history_connection as _open_and_initialize_history_connection_helper,
)


def initialize_history_store_runtime(
    store: Any,
    *,
    db_path: str,
    max_rows: int,
    retention_days: int,
    event_max_rows: int,
    event_retention_days: int,
    rollup_retention_days: int,
    lock_factory: Callable[[], Any] = threading.Lock,
    open_and_initialize_history_connection_fn: Callable[..., Any] = _open_and_initialize_history_connection_helper,
) -> None:
    store.db_path = db_path
    store.max_rows = max(100, int(max_rows))
    store.retention_seconds = max(0, int(retention_days)) * 86400
    store.event_max_rows = max(1000, int(event_max_rows))
    store.event_retention_seconds = max(0, int(event_retention_days)) * 86400
    store.rollup_retention_seconds = max(0, int(rollup_retention_days)) * 86400
    store._writes_since_prune = 0
    store._lock = lock_factory()
    store._conn = open_and_initialize_history_connection_fn(
        db_path=store.db_path,
        retention_seconds=store.retention_seconds,
        event_retention_seconds=store.event_retention_seconds,
        rollup_retention_seconds=store.rollup_retention_seconds,
        max_rows=store.max_rows,
        event_max_rows=store.event_max_rows,
    )
