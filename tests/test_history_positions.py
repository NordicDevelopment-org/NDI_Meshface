import sqlite3

from meshdash.history_positions import insert_node_position_if_changed
from meshdash.history.db import initialize_history_schema


def test_insert_node_position_if_changed_inserts_valid_position():
    conn = sqlite3.connect(":memory:")
    try:
        initialize_history_schema(conn)
        insert_node_position_if_changed(
            conn,
            node_id="!n1",
            event_unix=100,
            position_data={
                "latitude": 44.95,
                "longitude": -93.10,
                "altitude_m": "281.2",
                "satsInView": "9",
            },
        )
        row = conn.execute(
            "SELECT created_unix, node_id, lat, lon, altitude, sats_in_view FROM node_positions"
        ).fetchone()

        assert row == (100, "!n1", 44.95, -93.1, 281.2, 9)
    finally:
        conn.close()


def test_insert_node_position_if_changed_skips_duplicate_within_30_seconds():
    conn = sqlite3.connect(":memory:")
    try:
        initialize_history_schema(conn)
        insert_node_position_if_changed(
            conn,
            node_id="!n1",
            event_unix=100,
            position_data={"latitude": 44.95, "longitude": -93.10},
        )
        insert_node_position_if_changed(
            conn,
            node_id="!n1",
            event_unix=120,
            position_data={"latitude": 44.95, "longitude": -93.10},
        )
        count = conn.execute("SELECT COUNT(*) FROM node_positions").fetchone()[0]
        assert count == 1
    finally:
        conn.close()


def test_insert_node_position_if_changed_inserts_after_duplicate_window():
    conn = sqlite3.connect(":memory:")
    try:
        initialize_history_schema(conn)
        insert_node_position_if_changed(
            conn,
            node_id="!n1",
            event_unix=100,
            position_data={"latitude": 44.95, "longitude": -93.10},
        )
        insert_node_position_if_changed(
            conn,
            node_id="!n1",
            event_unix=140,
            position_data={"latitude": 44.95, "longitude": -93.10},
        )
        count = conn.execute("SELECT COUNT(*) FROM node_positions").fetchone()[0]
        assert count == 2
    finally:
        conn.close()
