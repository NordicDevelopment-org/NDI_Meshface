from collections.abc import Iterable
from typing import Optional

from .helpers import format_epoch as _format_epoch
from .helpers import to_int as _to_int
from .history_queries import PACKET_TYPE_CASE_SQL
from .history_store_runtime_contracts import HistoryStoreReadState
from .sql_contracts import SqlConnection, SqlRows


_DEFAULT_LIMIT = 10
_MAX_LIMIT = 50

TOP_NODE_CATEGORIES: tuple[dict[str, str], ...] = (
    {
        "id": "saved_packets",
        "label": "Saved Packets",
        "unit": "packets",
        "source": "node_saved_counts",
    },
    {
        "id": "active_hours",
        "label": "Active Hours",
        "unit": "hours",
        "source": "node_hour_seen",
    },
    {
        "id": "chat_packets",
        "label": "Chats",
        "unit": "chats",
        "source": "packet_events",
    },
    {
        "id": "gps_positions",
        "label": "GPS Positions",
        "unit": "positions",
        "source": "node_positions",
    },
    {
        "id": "environment_metrics",
        "label": "Metrics",
        "unit": "samples",
        "source": "environment_metrics_1m",
    },
    {
        "id": "links",
        "label": "Links",
        "unit": "links",
        "source": "connections",
    },
    {
        "id": "link_packets",
        "label": "Link Packets",
        "unit": "packets",
        "source": "connections",
    },
    {
        "id": "telemetry_packets",
        "label": "Telemetry",
        "unit": "packets",
        "source": "packet_events",
    },
    {
        "id": "position_packets",
        "label": "Position Packets",
        "unit": "packets",
        "source": "packet_events",
    },
    {
        "id": "routing_packets",
        "label": "Routing",
        "unit": "packets",
        "source": "packet_events",
    },
    {
        "id": "nodeinfo_packets",
        "label": "Node Info",
        "unit": "packets",
        "source": "packet_events",
    },
    {
        "id": "direct_packets",
        "label": "Direct Sends",
        "unit": "packets",
        "source": "packet_events",
    },
    {
        "id": "storeforward_packets",
        "label": "Store/Fwd",
        "unit": "packets",
        "source": "packet_events",
    },
    {
        "id": "admin_packets",
        "label": "Admin",
        "unit": "packets",
        "source": "packet_events",
    },
    {
        "id": "encrypted_packets",
        "label": "Encrypted",
        "unit": "packets",
        "source": "packet_events",
    },
    {
        "id": "other_packets",
        "label": "Other Packets",
        "unit": "packets",
        "source": "packet_events",
    },
)

_CATEGORY_BY_ID = {entry["id"]: entry for entry in TOP_NODE_CATEGORIES}

_PORT_CATEGORY_TO_PORTNUM = {
    "chat_packets": "TEXT_MESSAGE_APP",
    "telemetry_packets": "TELEMETRY_APP",
    "position_packets": "POSITION_APP",
    "routing_packets": "ROUTING_APP",
    "nodeinfo_packets": "NODEINFO_APP",
    "storeforward_packets": "STORE_FORWARD_APP",
    "admin_packets": "ADMIN_APP",
}


def normalize_top_node_category(raw_category: object) -> str:
    clean = str(raw_category or "").strip().lower().replace("-", "_")
    aliases = {
        "packets": "saved_packets",
        "stored_packets": "saved_packets",
        "saved": "saved_packets",
        "uptime": "active_hours",
        "active": "active_hours",
        "chats": "chat_packets",
        "chat": "chat_packets",
        "gps": "gps_positions",
        "positions": "gps_positions",
        "position": "position_packets",
        "metrics": "environment_metrics",
        "metric": "environment_metrics",
        "telemetry": "telemetry_packets",
        "link": "links",
        "link_count": "links",
        "link_packets": "link_packets",
        "routing": "routing_packets",
        "nodeinfo": "nodeinfo_packets",
        "node_info": "nodeinfo_packets",
        "direct": "direct_packets",
        "store_forward": "storeforward_packets",
        "storefwd": "storeforward_packets",
        "encrypted": "encrypted_packets",
        "other": "other_packets",
    }
    clean = aliases.get(clean, clean)
    return clean if clean in _CATEGORY_BY_ID else "saved_packets"


def _clean_limit(limit: object) -> int:
    parsed = _to_int(limit)
    if parsed is None:
        parsed = _DEFAULT_LIMIT
    return max(1, min(_MAX_LIMIT, int(parsed)))


def _valid_node_clause(column_name: str = "node_id") -> str:
    return (
        f"trim(COALESCE({column_name}, '')) <> '' "
        f"AND trim(COALESCE({column_name}, '')) NOT IN ('Unknown', 'n/a', '^all')"
    )


def _fetch_saved_packet_rows(conn: SqlConnection, limit: int) -> SqlRows:
    return conn.execute(
        f"""
        SELECT node_id,
               saved_packets AS value,
               saved_points AS secondary_value,
               saved_last_seen_unix AS last_seen_unix
        FROM node_saved_counts
        WHERE {_valid_node_clause("node_id")}
          AND COALESCE(saved_packets, 0) > 0
        ORDER BY saved_packets DESC, saved_last_seen_unix DESC, node_id ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def _fetch_active_hour_rows(conn: SqlConnection, limit: int) -> SqlRows:
    return conn.execute(
        f"""
        SELECT node_id,
               COUNT(*) AS value,
               NULL AS secondary_value,
               MAX(hour_bucket) AS last_seen_unix
        FROM node_hour_seen
        WHERE {_valid_node_clause("node_id")}
        GROUP BY node_id
        HAVING value > 0
        ORDER BY value DESC, last_seen_unix DESC, node_id ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def _fetch_gps_position_rows(conn: SqlConnection, limit: int) -> SqlRows:
    return conn.execute(
        f"""
        SELECT node_id,
               COUNT(*) AS value,
               NULL AS secondary_value,
               MAX(created_unix) AS last_seen_unix
        FROM node_positions
        WHERE {_valid_node_clause("node_id")}
        GROUP BY node_id
        HAVING value > 0
        ORDER BY value DESC, last_seen_unix DESC, node_id ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def _fetch_environment_metric_rows(conn: SqlConnection, limit: int) -> SqlRows:
    return conn.execute(
        f"""
        SELECT node_id,
               SUM(sample_count) AS value,
               COUNT(DISTINCT metric_key) AS secondary_value,
               MAX(last_seen_unix) AS last_seen_unix
        FROM environment_metrics_1m
        WHERE {_valid_node_clause("node_id")}
        GROUP BY node_id
        HAVING value > 0
        ORDER BY value DESC, last_seen_unix DESC, node_id ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def _fetch_link_rows(conn: SqlConnection, *, limit: int, by_packets: bool) -> SqlRows:
    value_expr = "SUM(seen_count)" if by_packets else "COUNT(DISTINCT peer_id)"
    secondary_expr = "COUNT(DISTINCT peer_id)" if by_packets else "SUM(seen_count)"
    return conn.execute(
        f"""
        SELECT node_id,
               {value_expr} AS value,
               {secondary_expr} AS secondary_value,
               MAX(last_seen_unix) AS last_seen_unix
        FROM (
          SELECT from_id AS node_id, to_id AS peer_id, seen_count, last_seen_unix
          FROM connections
          WHERE {_valid_node_clause("from_id")}
            AND {_valid_node_clause("to_id")}
          UNION ALL
          SELECT to_id AS node_id, from_id AS peer_id, seen_count, last_seen_unix
          FROM connections
          WHERE {_valid_node_clause("to_id")}
            AND {_valid_node_clause("from_id")}
        )
        GROUP BY node_id
        HAVING value > 0
        ORDER BY value DESC, last_seen_unix DESC, node_id ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def _fetch_direct_packet_rows(conn: SqlConnection, limit: int) -> SqlRows:
    return conn.execute(
        f"""
        SELECT from_id AS node_id,
               COUNT(*) AS value,
               COUNT(DISTINCT to_id) AS secondary_value,
               MAX(created_unix) AS last_seen_unix
        FROM packet_events
        WHERE {_valid_node_clause("from_id")}
          AND {_valid_node_clause("to_id")}
          AND from_id <> to_id
        GROUP BY from_id
        HAVING value > 0
        ORDER BY value DESC, last_seen_unix DESC, node_id ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def _fetch_packet_category_rows(conn: SqlConnection, *, category: str, limit: int) -> SqlRows:
    portnum = _PORT_CATEGORY_TO_PORTNUM.get(category)
    if portnum:
        return conn.execute(
            f"""
            SELECT from_id AS node_id,
                   COUNT(*) AS value,
                   COUNT(DISTINCT to_id) AS secondary_value,
                   MAX(created_unix) AS last_seen_unix
            FROM packet_events
            WHERE {_valid_node_clause("from_id")}
              AND upper(trim(COALESCE(portnum, ''))) = ?
            GROUP BY from_id
            HAVING value > 0
            ORDER BY value DESC, last_seen_unix DESC, node_id ASC
            LIMIT ?
            """,
            (portnum, limit),
        ).fetchall()

    if category == "encrypted_packets":
        return conn.execute(
            f"""
            SELECT from_id AS node_id,
                   COUNT(*) AS value,
                   COUNT(DISTINCT to_id) AS secondary_value,
                   MAX(created_unix) AS last_seen_unix
            FROM packet_events
            WHERE {_valid_node_clause("from_id")}
              AND trim(COALESCE(portnum, '')) = ''
            GROUP BY from_id
            HAVING value > 0
            ORDER BY value DESC, last_seen_unix DESC, node_id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    if category == "other_packets":
        return conn.execute(
            f"""
            SELECT from_id AS node_id,
                   COUNT(*) AS value,
                   COUNT(DISTINCT to_id) AS secondary_value,
                   MAX(created_unix) AS last_seen_unix
            FROM packet_events
            WHERE {_valid_node_clause("from_id")}
              AND ({PACKET_TYPE_CASE_SQL}) = 'other'
            GROUP BY from_id
            HAVING value > 0
            ORDER BY value DESC, last_seen_unix DESC, node_id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return conn.execute(
        f"""
        SELECT from_id AS node_id,
               COUNT(*) AS value,
               COUNT(DISTINCT to_id) AS secondary_value,
               MAX(created_unix) AS last_seen_unix
        FROM packet_events
        WHERE {_valid_node_clause("from_id")}
        GROUP BY from_id
        HAVING value > 0
        ORDER BY value DESC, last_seen_unix DESC, node_id ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def _fetch_category_rows(conn: SqlConnection, category: str, limit: int) -> SqlRows:
    if category == "saved_packets":
        return _fetch_saved_packet_rows(conn, limit)
    if category == "active_hours":
        return _fetch_active_hour_rows(conn, limit)
    if category == "gps_positions":
        return _fetch_gps_position_rows(conn, limit)
    if category == "environment_metrics":
        return _fetch_environment_metric_rows(conn, limit)
    if category == "links":
        return _fetch_link_rows(conn, limit=limit, by_packets=False)
    if category == "link_packets":
        return _fetch_link_rows(conn, limit=limit, by_packets=True)
    if category == "direct_packets":
        return _fetch_direct_packet_rows(conn, limit)
    return _fetch_packet_category_rows(conn, category=category, limit=limit)


def _item_from_row(row: object, rank: int) -> dict[str, object] | None:
    if isinstance(row, tuple):
        raw = row
    elif isinstance(row, list):
        raw = tuple(row)
    else:
        try:
            raw = tuple(row)  # type: ignore[arg-type]
        except Exception:
            return None
    if len(raw) < 2:
        return None

    node_id = str(raw[0] or "").strip()
    if not node_id:
        return None
    value = _to_int(raw[1])
    if value is None or value <= 0:
        return None
    secondary = _to_int(raw[2]) if len(raw) > 2 else None
    last_seen_unix = _to_int(raw[3]) if len(raw) > 3 else None

    item: dict[str, object] = {
        "rank": rank,
        "node_id": node_id,
        "value": int(value),
    }
    if secondary is not None:
        item["secondary_value"] = int(secondary)
    if last_seen_unix is not None and last_seen_unix > 0:
        item["last_seen_unix"] = int(last_seen_unix)
        item["last_seen"] = _format_epoch(last_seen_unix)
    return item


def build_top_nodes_payload(
    *,
    category: object,
    rows: Iterable[object],
    limit: object = _DEFAULT_LIMIT,
) -> dict[str, object]:
    clean_category = normalize_top_node_category(category)
    clean_limit = _clean_limit(limit)
    category_meta = dict(_CATEGORY_BY_ID[clean_category])
    items: list[dict[str, object]] = []
    for row in rows:
        item = _item_from_row(row, len(items) + 1)
        if item is None:
            continue
        items.append(item)
        if len(items) >= clean_limit:
            break
    return {
        "ok": True,
        "category": clean_category,
        "category_label": category_meta.get("label") or clean_category,
        "unit": category_meta.get("unit") or "",
        "source": category_meta.get("source") or "history",
        "limit": clean_limit,
        "categories": [dict(entry) for entry in TOP_NODE_CATEGORIES],
        "items": items,
    }


def load_top_nodes(
    store: HistoryStoreReadState,
    *,
    category: object = "saved_packets",
    limit: object = _DEFAULT_LIMIT,
) -> dict[str, object]:
    clean_category = normalize_top_node_category(category)
    clean_limit = _clean_limit(limit)
    read_conn = getattr(store, "_read_conn", None)
    if read_conn is None or read_conn is store._conn:
        read_conn = store._conn
        read_lock = store._lock
    else:
        read_lock = getattr(store, "_read_lock", None) or store._lock
    with read_lock:
        rows = _fetch_category_rows(read_conn, clean_category, clean_limit)
    return build_top_nodes_payload(
        category=clean_category,
        rows=rows,
        limit=clean_limit,
    )
