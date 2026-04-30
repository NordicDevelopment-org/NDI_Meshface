import time
from collections.abc import Iterable

from .helpers import to_int as _to_int
from .history_store_runtime_contracts import HistoryStoreReadState
from .sql_contracts import SqlConnection, SqlRows


def _clean_node_id(value: object) -> str:
    text = str(value or "").strip()
    if not text or text in {"Unknown", "n/a", "^all", "^local"}:
        return ""
    return text


def _clamp_bucket_index(value: object, bucket_count: int) -> int:
    parsed = _to_int(value)
    if parsed is None:
        return 0
    return max(0, min(max(0, int(bucket_count) - 1), int(parsed)))


def _fetch_node_packet_trend_rows(
    conn: SqlConnection,
    *,
    cutoff_unix: int,
    now_unix: int,
    recent_cutoff_unix: int,
    bucket_span_seconds: int,
    local_node_id: str,
) -> SqlRows:
    # Match the browser's radio-activity filter: ignore admin frames, local-only
    # frames, and true self-to-self frames when a local node id is known.
    filter_sql = """
      created_unix >= ?
      AND created_unix <= ?
      AND COALESCE(UPPER(portnum), '') != 'ADMIN_APP'
      AND COALESCE(to_id, '') != '^local'
      AND NOT (? != '' AND from_id = ? AND to_id = ?)
    """
    bucket_expr = "CAST((created_unix - ?) / ? AS INTEGER)"
    sql = f"""
        SELECT direction,
               node_id,
               bucket_index,
               COUNT(*) AS packet_count,
               SUM(CASE WHEN created_unix >= ? THEN 1 ELSE 0 END) AS recent_count,
               MAX(created_unix) AS last_unix
        FROM (
          SELECT 'tx' AS direction,
                 from_id AS node_id,
                 {bucket_expr} AS bucket_index,
                 created_unix
          FROM packet_events
          WHERE {filter_sql}
            AND from_id IS NOT NULL
            AND from_id NOT IN ('', '^all', '^local', 'Unknown', 'n/a')
          UNION ALL
          SELECT 'rx' AS direction,
                 to_id AS node_id,
                 {bucket_expr} AS bucket_index,
                 created_unix
          FROM packet_events
          WHERE {filter_sql}
            AND to_id IS NOT NULL
            AND to_id NOT IN ('', '^all', '^local', 'Unknown', 'n/a')
        )
        GROUP BY direction, node_id, bucket_index
        ORDER BY node_id ASC, direction ASC, bucket_index ASC
    """
    params = (
        recent_cutoff_unix,
        cutoff_unix,
        bucket_span_seconds,
        cutoff_unix,
        now_unix,
        local_node_id,
        local_node_id,
        local_node_id,
        cutoff_unix,
        bucket_span_seconds,
        cutoff_unix,
        now_unix,
        local_node_id,
        local_node_id,
        local_node_id,
    )
    return conn.execute(sql, params).fetchall()


def _empty_node_packet_trends(
    *,
    window_seconds: int,
    bucket_count: int,
    bucket_span_seconds: int,
    recent_window_seconds: int,
    generated_unix: int,
) -> dict[str, object]:
    return {
        "ok": True,
        "source": "history",
        "window_seconds": window_seconds,
        "bucket_count": bucket_count,
        "bucket_span_seconds": bucket_span_seconds,
        "recent_window_seconds": recent_window_seconds,
        "generated_unix": generated_unix,
        "nodes": {},
    }


def build_node_packet_trends_payload(
    rows: Iterable[tuple[object, ...]],
    *,
    window_seconds: int,
    bucket_count: int,
    bucket_span_seconds: int,
    recent_window_seconds: int,
    generated_unix: int,
) -> dict[str, object]:
    nodes: dict[str, dict[str, object]] = {}
    for row in rows:
        if len(row) < 6:
            continue
        direction_raw, node_id_raw, bucket_index_raw, packet_count_raw, recent_count_raw, last_unix_raw = row[:6]
        direction = str(direction_raw or "").strip().lower()
        if direction not in {"tx", "rx"}:
            continue
        node_id = _clean_node_id(node_id_raw)
        if not node_id:
            continue
        packet_count = max(0, _to_int(packet_count_raw) or 0)
        if packet_count <= 0:
            continue
        recent_count = max(0, _to_int(recent_count_raw) or 0)
        last_unix = max(0, _to_int(last_unix_raw) or 0)
        bucket_index = _clamp_bucket_index(bucket_index_raw, bucket_count)
        node = nodes.get(node_id)
        if node is None:
            node = {
                "total": 0,
                "recent5m": 0,
                "txTotal": 0,
                "txRecent5m": 0,
                "rxTotal": 0,
                "rxRecent5m": 0,
                "lastPacketUnix": None,
                "lastTxUnix": None,
                "lastRxUnix": None,
                "buckets": [0 for _ in range(bucket_count)],
            }
            nodes[node_id] = node

        buckets = node["buckets"] if isinstance(node.get("buckets"), list) else []
        if buckets:
            buckets[bucket_index] = int(buckets[bucket_index] or 0) + packet_count

        if direction == "tx":
            node["txTotal"] = int(node["txTotal"] or 0) + packet_count
            node["txRecent5m"] = int(node["txRecent5m"] or 0) + recent_count
            node["lastTxUnix"] = max(int(node["lastTxUnix"] or 0), last_unix) or None
        else:
            node["rxTotal"] = int(node["rxTotal"] or 0) + packet_count
            node["rxRecent5m"] = int(node["rxRecent5m"] or 0) + recent_count
            node["lastRxUnix"] = max(int(node["lastRxUnix"] or 0), last_unix) or None

        node["total"] = int(node["txTotal"] or 0) + int(node["rxTotal"] or 0)
        node["recent5m"] = int(node["txRecent5m"] or 0) + int(node["rxRecent5m"] or 0)
        node["lastPacketUnix"] = max(
            int(node["lastTxUnix"] or 0),
            int(node["lastRxUnix"] or 0),
        ) or None

    return {
        "ok": True,
        "source": "history",
        "window_seconds": window_seconds,
        "bucket_count": bucket_count,
        "bucket_span_seconds": bucket_span_seconds,
        "recent_window_seconds": recent_window_seconds,
        "generated_unix": generated_unix,
        "nodes": nodes,
    }


def load_node_packet_trends(
    store: HistoryStoreReadState,
    *,
    local_node_id: str = "",
    window_seconds: int = 3600,
    bucket_count: int = 24,
    recent_window_seconds: int = 300,
) -> dict[str, object]:
    clean_window_seconds = max(60, min(24 * 3600, int(window_seconds or 3600)))
    clean_bucket_count = max(1, min(288, int(bucket_count or 24)))
    clean_recent_window_seconds = max(30, min(clean_window_seconds, int(recent_window_seconds or 300)))
    bucket_span_seconds = max(1, clean_window_seconds // clean_bucket_count)
    now_unix = int(time.time())
    cutoff_unix = now_unix - clean_window_seconds
    recent_cutoff_unix = now_unix - clean_recent_window_seconds
    clean_local_node_id = _clean_node_id(local_node_id)

    read_conn = getattr(store, "_read_conn", None)
    if read_conn is None or read_conn is store._conn:
        read_conn = store._conn
        read_lock = store._lock
    else:
        read_lock = getattr(store, "_read_lock", None) or store._lock

    with read_lock:
        rows = _fetch_node_packet_trend_rows(
            read_conn,
            cutoff_unix=cutoff_unix,
            now_unix=now_unix,
            recent_cutoff_unix=recent_cutoff_unix,
            bucket_span_seconds=bucket_span_seconds,
            local_node_id=clean_local_node_id,
        )

    if not rows:
        return _empty_node_packet_trends(
            window_seconds=clean_window_seconds,
            bucket_count=clean_bucket_count,
            bucket_span_seconds=bucket_span_seconds,
            recent_window_seconds=clean_recent_window_seconds,
            generated_unix=now_unix,
        )

    return build_node_packet_trends_payload(
        rows,
        window_seconds=clean_window_seconds,
        bucket_count=clean_bucket_count,
        bucket_span_seconds=bucket_span_seconds,
        recent_window_seconds=clean_recent_window_seconds,
        generated_unix=now_unix,
    )
