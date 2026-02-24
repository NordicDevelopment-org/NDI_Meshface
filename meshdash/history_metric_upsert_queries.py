from typing import Any, Iterable, Optional, Sequence


METRIC_FIELDS: tuple[str, ...] = (
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


def where_clause(*, key_fields: Sequence[str]) -> str:
    where_parts = ["bucket_unix = ?"] + [f"{field} = ?" for field in key_fields]
    return " AND ".join(where_parts)


def select_existing_row(
    conn: Any,
    *,
    table_name: str,
    key_fields: Sequence[str],
    bucket_unix: int,
    key_values: Sequence[Any],
) -> Optional[Iterable[Any]]:
    sql = (
        f"SELECT {', '.join(METRIC_FIELDS)} "
        f"FROM {table_name} "
        f"WHERE {where_clause(key_fields=key_fields)}"
    )
    return conn.execute(sql, (bucket_unix, *key_values)).fetchone()
