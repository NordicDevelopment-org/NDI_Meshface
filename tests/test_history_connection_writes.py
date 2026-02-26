import sqlite3

from meshdash.history_connection_writes import save_connection_event
from meshdash.history.db import initialize_history_schema


def test_save_connection_event_inserts_new_connection():
    conn = sqlite3.connect(":memory:")
    try:
        initialize_history_schema(conn)
        save_connection_event(
            conn,
            from_id="!a",
            to_id="!b",
            rx_time=100,
            portnum="TEXT_MESSAGE_APP",
            hops=2,
        )
        row = conn.execute(
            """
            SELECT first_seen_unix, last_seen_unix, seen_count,
                   portnums_json, last_hops, hops_sum, hops_count
            FROM connections
            WHERE from_id = ? AND to_id = ?
            """,
            ("!a", "!b"),
        ).fetchone()
        assert row == (100, 100, 1, '["TEXT_MESSAGE_APP"]', 2, 2, 1)
    finally:
        conn.close()


def test_save_connection_event_merges_existing_connection():
    conn = sqlite3.connect(":memory:")
    try:
        initialize_history_schema(conn)
        save_connection_event(
            conn,
            from_id="!a",
            to_id="!b",
            rx_time=100,
            portnum="NODEINFO_APP",
            hops=1,
        )
        save_connection_event(
            conn,
            from_id="!a",
            to_id="!b",
            rx_time=120,
            portnum="TEXT_MESSAGE_APP",
            hops=3,
        )
        row = conn.execute(
            """
            SELECT first_seen_unix, last_seen_unix, seen_count,
                   portnums_json, last_hops, hops_sum, hops_count
            FROM connections
            WHERE from_id = ? AND to_id = ?
            """,
            ("!a", "!b"),
        ).fetchone()
        assert row == (100, 120, 2, '["NODEINFO_APP","TEXT_MESSAGE_APP"]', 3, 4, 2)
    finally:
        conn.close()
