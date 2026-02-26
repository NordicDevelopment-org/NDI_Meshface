import sqlite3

from meshdash.history.db import initialize_history_schema
from meshdash.history_writes import save_packet_event_and_rollups


def test_save_packet_event_and_rollups_updates_node_history_surfaces():
    conn = sqlite3.connect(":memory:")
    try:
        initialize_history_schema(conn)
        summary = {
            "from": "!n1",
            "to": "^all",
            "rx_time_unix": 120,
            "rx_snr": 6.5,
            "rx_rssi": -98,
            "hops": 2,
            "portnum": "TEXT_MESSAGE_APP",
            "position": {"lat": 44.95, "lon": -93.10, "sats_in_view": 7},
            "battery_level": 83,
        }
        save_packet_event_and_rollups(conn, summary)

        assert conn.execute("SELECT COUNT(*) FROM packet_events").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM node_metrics_1m").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM node_positions").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM node_capabilities").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM link_metrics_1m").fetchone()[0] == 0

        cap = conn.execute(
            """
            SELECT last_seen_unix, has_position, last_position_unix,
                   last_hops, battery_level, battery_updated_unix
            FROM node_capabilities
            WHERE node_id = ?
            """,
            ("!n1",),
        ).fetchone()
        assert cap == (120, 1, 120, 2, 83, 120)
    finally:
        conn.close()


def test_save_packet_event_and_rollups_updates_link_metrics_for_direct_edges():
    conn = sqlite3.connect(":memory:")
    try:
        initialize_history_schema(conn)
        save_packet_event_and_rollups(
            conn,
            {
                "from": "!n1",
                "to": "!n2",
                "rx_time_unix": 60,
                "rx_snr": 2.0,
                "rx_rssi": -101.0,
                "hops": 1,
                "portnum": "NODEINFO_APP",
            },
        )
        save_packet_event_and_rollups(
            conn,
            {
                "from": "!n1",
                "to": "!n2",
                "rx_time_unix": 85,
                "rx_snr": 4.0,
                "rx_rssi": -99.0,
                "hops": 2,
                "portnum": "TEXT_MESSAGE_APP",
            },
        )

        row = conn.execute(
            """
            SELECT packet_count, snr_count, snr_min, snr_max,
                   rssi_count, rssi_min, rssi_max,
                   hops_count, hops_min, hops_max, last_seen_unix
            FROM link_metrics_1m
            WHERE bucket_unix = ? AND from_id = ? AND to_id = ?
            """,
            (60, "!n1", "!n2"),
        ).fetchone()

        assert row is not None
        assert row[0] == 2
        assert row[1] == 2
        assert row[2] == 2.0
        assert row[3] == 4.0
        assert row[4] == 2
        assert row[5] == -101.0
        assert row[6] == -99.0
        assert row[7] == 2
        assert row[8] == 1
        assert row[9] == 2
        assert row[10] == 85
    finally:
        conn.close()
