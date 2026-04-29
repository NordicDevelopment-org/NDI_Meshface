from .history_schema_indexes import (
    INDEX_SCHEMA_STATEMENTS as _INDEX_SCHEMA_STATEMENTS,
)
from .history_schema_tables import (
    TABLE_SCHEMA_STATEMENTS as _TABLE_SCHEMA_STATEMENTS,
)
from .history_schema_triggers import (
    TRIGGER_SCHEMA_STATEMENTS as _TRIGGER_SCHEMA_STATEMENTS,
)
from .sql_contracts import SqlConnection


SCHEMA_STATEMENTS = _TABLE_SCHEMA_STATEMENTS + _INDEX_SCHEMA_STATEMENTS + _TRIGGER_SCHEMA_STATEMENTS


def _table_column_names(conn: SqlConnection, table_name: str) -> set[str]:
    safe_name = str(table_name or "").replace('"', '""')
    rows = conn.execute(f'PRAGMA table_info("{safe_name}")').fetchall()
    names: set[str] = set()
    for row in rows:
        if not row or len(row) < 2:
            continue
        name = row[1]
        if isinstance(name, str) and name:
            names.add(name)
    return names


def _ensure_summary_metrics_compat_columns(conn: SqlConnection) -> None:
    columns = _table_column_names(conn, "summary_metrics_1m")
    if "saved_node_count" not in columns:
        conn.execute(
            """
            ALTER TABLE summary_metrics_1m
            ADD COLUMN saved_node_count INTEGER NOT NULL DEFAULT 0
            """
        )
        columns.add("saved_node_count")
    if "online_node_count" not in columns:
        conn.execute(
            """
            ALTER TABLE summary_metrics_1m
            ADD COLUMN online_node_count INTEGER NOT NULL DEFAULT 0
            """
        )
        columns.add("online_node_count")
    if "edge_count" not in columns:
        conn.execute(
            """
            ALTER TABLE summary_metrics_1m
            ADD COLUMN edge_count INTEGER NOT NULL DEFAULT 0
            """
        )
        conn.execute(
            """
            UPDATE summary_metrics_1m
            SET edge_count = real_edge_count
            WHERE edge_count <= 0 AND real_edge_count > 0
            """
        )


def _ensure_node_capabilities_compat_columns(conn: SqlConnection) -> None:
    columns = _table_column_names(conn, "node_capabilities")
    first_seen_missing = "first_seen_unix" not in columns
    if first_seen_missing:
        conn.execute(
            """
            ALTER TABLE node_capabilities
            ADD COLUMN first_seen_unix INTEGER
            """
        )
        columns.add("first_seen_unix")
    if "last_short_name" not in columns:
        conn.execute(
            """
            ALTER TABLE node_capabilities
            ADD COLUMN last_short_name TEXT
            """
        )
        columns.add("last_short_name")
    if "last_long_name" not in columns:
        conn.execute(
            """
            ALTER TABLE node_capabilities
            ADD COLUMN last_long_name TEXT
            """
        )
        columns.add("last_long_name")
    if "names_updated_unix" not in columns:
        conn.execute(
            """
            ALTER TABLE node_capabilities
            ADD COLUMN names_updated_unix INTEGER
            """
        )
    if first_seen_missing:
        conn.execute(
            """
            UPDATE node_capabilities
            SET first_seen_unix = (
              SELECT MIN(candidate_unix)
              FROM (
                SELECT MIN(last_seen_unix) AS candidate_unix
                FROM node_metrics_1m
                WHERE node_id = node_capabilities.node_id
                UNION ALL
                SELECT MIN(created_unix) AS candidate_unix
                FROM node_positions
                WHERE node_id = node_capabilities.node_id
                UNION ALL
                SELECT MIN(created_unix) AS candidate_unix
                FROM packet_events
                WHERE from_id = node_capabilities.node_id
                UNION ALL
                SELECT last_seen_unix AS candidate_unix
                FROM node_capabilities AS fallback_caps
                WHERE fallback_caps.node_id = node_capabilities.node_id
              )
              WHERE candidate_unix IS NOT NULL AND candidate_unix > 0
            )
            WHERE first_seen_unix IS NULL OR first_seen_unix <= 0
            """
        )


def initialize_history_schema(conn: SqlConnection) -> None:
    for statement in SCHEMA_STATEMENTS:
        conn.execute(statement)
    _ensure_summary_metrics_compat_columns(conn)
    _ensure_node_capabilities_compat_columns(conn)
