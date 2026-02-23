from typing import Any, Callable, Iterable, Optional, Sequence


_METRIC_FIELDS: tuple[str, ...] = (
    "packet_count",
    "snr_sum",
    "snr_count",
    "snr_min",
    "snr_max",
    "rssi_sum",
    "rssi_count",
    "rssi_min",
    "rssi_max",
    "hops_sum",
    "hops_count",
    "hops_min",
    "hops_max",
    "last_seen_unix",
)


def _where_clause(*, key_fields: Sequence[str]) -> str:
    where_parts = ["bucket_unix = ?"] + [f"{field} = ?" for field in key_fields]
    return " AND ".join(where_parts)


def _select_existing_row(
    conn: Any,
    *,
    table_name: str,
    key_fields: Sequence[str],
    bucket_unix: int,
    key_values: Sequence[Any],
) -> Optional[Iterable[Any]]:
    sql = (
        f"SELECT {', '.join(_METRIC_FIELDS)} "
        f"FROM {table_name} "
        f"WHERE {_where_clause(key_fields=key_fields)}"
    )
    return conn.execute(sql, (bucket_unix, *key_values)).fetchone()


def _insert_metric_row(
    conn: Any,
    *,
    table_name: str,
    key_fields: Sequence[str],
    bucket_unix: int,
    key_values: Sequence[Any],
    rolled: dict,
) -> None:
    fields = ("bucket_unix", *key_fields, *_METRIC_FIELDS)
    placeholders = ", ".join("?" for _ in fields)
    sql = f"INSERT INTO {table_name}({', '.join(fields)}) VALUES({placeholders})"
    values = (bucket_unix, *key_values, *[rolled[field] for field in _METRIC_FIELDS])
    conn.execute(sql, values)


def _update_metric_row(
    conn: Any,
    *,
    table_name: str,
    key_fields: Sequence[str],
    bucket_unix: int,
    key_values: Sequence[Any],
    merged: dict,
) -> None:
    assignments = ", ".join(f"{field} = ?" for field in _METRIC_FIELDS)
    sql = (
        f"UPDATE {table_name} "
        f"SET {assignments} "
        f"WHERE {_where_clause(key_fields=key_fields)}"
    )
    values = (*[merged[field] for field in _METRIC_FIELDS], bucket_unix, *key_values)
    conn.execute(sql, values)


def upsert_metric_rollup_row(
    conn: Any,
    *,
    table_name: str,
    key_fields: Sequence[str],
    key_values: Sequence[Any],
    bucket_unix: int,
    event_unix: int,
    rx_snr: Optional[float],
    rx_rssi: Optional[float],
    hops: Optional[int],
    build_metric_rollup_values_fn: Callable[..., dict],
    merge_metric_rollup_row_fn: Callable[..., dict],
) -> None:
    row = _select_existing_row(
        conn,
        table_name=table_name,
        key_fields=key_fields,
        bucket_unix=bucket_unix,
        key_values=key_values,
    )

    if row is None:
        rolled = build_metric_rollup_values_fn(
            event_unix=event_unix,
            rx_snr=rx_snr,
            rx_rssi=rx_rssi,
            hops=hops,
        )
        _insert_metric_row(
            conn,
            table_name=table_name,
            key_fields=key_fields,
            bucket_unix=bucket_unix,
            key_values=key_values,
            rolled=rolled,
        )
        return

    merged = merge_metric_rollup_row_fn(
        row=row,
        event_unix=event_unix,
        rx_snr=rx_snr,
        rx_rssi=rx_rssi,
        hops=hops,
    )
    _update_metric_row(
        conn,
        table_name=table_name,
        key_fields=key_fields,
        bucket_unix=bucket_unix,
        key_values=key_values,
        merged=merged,
    )
