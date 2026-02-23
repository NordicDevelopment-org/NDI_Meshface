import sqlite3

from meshdash.history_capability_writes import upsert_node_capability
from meshdash.history_schema import initialize_history_schema


def test_upsert_node_capability_inserts_new_node():
    conn = sqlite3.connect(":memory:")
    try:
        initialize_history_schema(conn)
        upsert_node_capability(
            conn,
            node_id="!n1",
            event_unix=120,
            has_position=True,
            last_hops=2,
            battery_level=83,
        )
        row = conn.execute(
            """
            SELECT last_seen_unix, has_position, last_position_unix,
                   last_hops, battery_level, battery_updated_unix
            FROM node_capabilities
            WHERE node_id = ?
            """,
            ("!n1",),
        ).fetchone()
        assert row == (120, 1, 120, 2, 83, 120)
    finally:
        conn.close()


def test_upsert_node_capability_merges_existing_node():
    conn = sqlite3.connect(":memory:")
    try:
        initialize_history_schema(conn)
        upsert_node_capability(
            conn,
            node_id="!n1",
            event_unix=120,
            has_position=True,
            last_hops=2,
            battery_level=83,
        )
        upsert_node_capability(
            conn,
            node_id="!n1",
            event_unix=180,
            has_position=False,
            last_hops=4,
            battery_level=79,
        )
        row = conn.execute(
            """
            SELECT last_seen_unix, has_position, last_position_unix,
                   last_hops, battery_level, battery_updated_unix
            FROM node_capabilities
            WHERE node_id = ?
            """,
            ("!n1",),
        ).fetchone()
        assert row == (180, 1, 120, 4, 79, 180)
    finally:
        conn.close()
