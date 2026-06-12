import os
import time

from .history_store_runtime_contracts import HistoryStoreReadState

_COUNTED_TABLES: tuple[str, ...] = (
    "packets",
    "packet_events",
    "chat",
    "connections",
    "node_capabilities",
    "node_saved_counts",
    "node_position_counts",
    "node_positions",
    "node_metrics_1m",
    "link_metrics_1m",
    "summary_metrics_1m",
    "environment_metrics_1m",
    "malformed_text_payloads",
    "node_hour_seen",
    "dashboard_settings",
)

_RANGE_TABLES: tuple[tuple[str, str], ...] = (
    ("packets", "created_unix"),
    ("packet_events", "created_unix"),
    ("chat", "created_unix"),
    ("node_metrics_1m", "last_seen_unix"),
    ("link_metrics_1m", "last_seen_unix"),
    ("summary_metrics_1m", "last_seen_unix"),
    ("environment_metrics_1m", "last_seen_unix"),
)


def _sql_identifier(name: str) -> str:
    return str(name).replace('"', '""')


def _fetch_one_int(conn: object, sql: str) -> int | None:
    row = conn.execute(sql).fetchone()
    if not row:
        return None
    value = row[0]
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _table_names(conn: object) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    names: set[str] = set()
    for row in rows:
        if not row:
            continue
        name = row[0]
        if isinstance(name, str) and name:
            names.add(name)
    return names


def _count_rows(conn: object, table_name: str) -> int:
    safe_name = _sql_identifier(table_name)
    value = _fetch_one_int(conn, f'SELECT COUNT(*) FROM "{safe_name}"')
    return max(0, int(value or 0))


def _range_for(conn: object, table_name: str, column_name: str) -> dict[str, int | None]:
    safe_table = _sql_identifier(table_name)
    safe_column = _sql_identifier(column_name)
    row = conn.execute(
        f'SELECT MIN("{safe_column}"), MAX("{safe_column}") FROM "{safe_table}"'
    ).fetchone()
    if not row:
        return {"first_unix": None, "last_unix": None}

    first_unix: int | None
    last_unix: int | None
    try:
        first_unix = int(row[0]) if row[0] is not None else None
    except Exception:
        first_unix = None
    try:
        last_unix = int(row[1]) if row[1] is not None else None
    except Exception:
        last_unix = None
    return {"first_unix": first_unix, "last_unix": last_unix}


def _pragma_int(conn: object, name: str) -> int | None:
    safe_name = "".join(ch for ch in str(name) if ch.isalnum() or ch == "_")
    if not safe_name:
        return None
    return _fetch_one_int(conn, f"PRAGMA {safe_name}")


def _file_size(path: str) -> int | None:
    clean_path = str(path or "").strip()
    if not clean_path or clean_path in {":memory:", "file::memory:"}:
        return None
    try:
        return int(os.path.getsize(clean_path))
    except Exception:
        return None


def _days_from_seconds(seconds: object) -> int | None:
    try:
        clean_seconds = int(seconds)
    except Exception:
        return None
    if clean_seconds <= 0:
        return 0
    return int(clean_seconds // 86400)


def load_database_stats(store: HistoryStoreReadState) -> dict[str, object]:
    """Return lightweight, on-demand SQLite history database statistics."""
    read_conn = getattr(store, "_read_conn", None)
    if read_conn is None or read_conn is store._conn:
        read_conn = store._conn
        read_lock = store._lock
    else:
        read_lock = getattr(store, "_read_lock", None) or store._lock

    with read_lock:
        tables = _table_names(read_conn)
        table_counts = {
            table_name: _count_rows(read_conn, table_name)
            for table_name in _COUNTED_TABLES
            if table_name in tables
        }
        ranges = {
            table_name: _range_for(read_conn, table_name, column_name)
            for table_name, column_name in _RANGE_TABLES
            if table_name in tables
        }
        page_count = _pragma_int(read_conn, "page_count")
        page_size = _pragma_int(read_conn, "page_size")
        freelist_count = _pragma_int(read_conn, "freelist_count")

    db_path = str(getattr(store, "db_path", "") or "")
    db_size = _file_size(db_path)
    wal_size = _file_size(f"{db_path}-wal") if db_path else None
    shm_size = _file_size(f"{db_path}-shm") if db_path else None
    total_size = sum(size for size in (db_size, wal_size, shm_size) if isinstance(size, int))

    retention_seconds = int(getattr(store, "retention_seconds", 0) or 0)
    event_retention_seconds = int(getattr(store, "event_retention_seconds", 0) or 0)
    rollup_retention_seconds = int(getattr(store, "rollup_retention_seconds", 0) or 0)

    return {
        "ok": True,
        "enabled": True,
        "source": "history_store",
        "generated_unix": int(time.time()),
        "path": db_path,
        "size_bytes": db_size,
        "wal_size_bytes": wal_size,
        "shm_size_bytes": shm_size,
        "total_size_bytes": total_size,
        "page_count": page_count,
        "page_size": page_size,
        "freelist_count": freelist_count,
        "table_counts": table_counts,
        "total_rows": sum(table_counts.values()),
        "ranges": ranges,
        "policy": {
            "max_rows": int(getattr(store, "max_rows", 0) or 0),
            "retention_seconds": retention_seconds,
            "retention_days": _days_from_seconds(retention_seconds),
            "event_max_rows": int(getattr(store, "event_max_rows", 0) or 0),
            "event_retention_seconds": event_retention_seconds,
            "event_retention_days": _days_from_seconds(event_retention_seconds),
            "rollup_retention_seconds": rollup_retention_seconds,
            "rollup_retention_days": _days_from_seconds(rollup_retention_seconds),
        },
    }
