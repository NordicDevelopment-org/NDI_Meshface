import sqlite3

from meshdash.history_backfill import backfill_node_capabilities
from meshdash.history_schema import initialize_history_schema


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def test_backfill_node_capabilities_populates_from_history_tables():
    conn = sqlite3.connect(":memory:")
    try:
        initialize_history_schema(conn)
        conn.execute(
            """
            INSERT INTO node_metrics_1m(
              bucket_unix, node_id, packet_count,
              snr_sum, snr_count, snr_min, snr_max,
              rssi_sum, rssi_count, rssi_min, rssi_max,
              hops_sum, hops_count, hops_min, hops_max,
              last_seen_unix
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (60, "!n1", 1, 0.0, 0, None, None, 0.0, 0, None, None, 0, 0, None, None, 100),
        )
        conn.execute(
            """
            INSERT INTO node_positions(created_unix, node_id, lat, lon, altitude, sats_in_view)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (120, "!n1", 44.95, -93.10, None, None),
        )
        conn.execute(
            """
            INSERT INTO packet_events(
              created_unix, from_id, to_id, portnum,
              rx_snr, rx_rssi, hops, hop_start, hop_limit,
              channel, want_ack, priority, summary_json
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (130, "!n1", "^all", "TEXT_MESSAGE_APP", None, None, 3, None, None, None, None, None, "{}"),
        )

        backfill_node_capabilities(conn, to_int_fn=_to_int)

        row = conn.execute(
            """
            SELECT last_seen_unix, has_position, last_position_unix,
                   last_hops, battery_level, battery_updated_unix
            FROM node_capabilities
            WHERE node_id = ?
            """,
            ("!n1",),
        ).fetchone()

        assert row is not None
        assert row[0] == 130
        assert row[1] == 1
        assert row[2] == 120
        assert row[3] == 3
        assert row[4] is None
        assert row[5] is None
    finally:
        conn.close()


def test_backfill_node_capabilities_is_noop_when_capabilities_exist():
    conn = sqlite3.connect(":memory:")
    try:
        initialize_history_schema(conn)
        conn.execute(
            """
            INSERT INTO node_capabilities(
              node_id, last_seen_unix, has_position, last_position_unix,
              last_hops, battery_level, battery_updated_unix
            ) VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            ("!existing", 50, 0, None, None, None, None),
        )
        conn.execute(
            """
            INSERT INTO node_metrics_1m(
              bucket_unix, node_id, packet_count,
              snr_sum, snr_count, snr_min, snr_max,
              rssi_sum, rssi_count, rssi_min, rssi_max,
              hops_sum, hops_count, hops_min, hops_max,
              last_seen_unix
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (120, "!new", 1, 0.0, 0, None, None, 0.0, 0, None, None, 0, 0, None, None, 999),
        )

        backfill_node_capabilities(conn, to_int_fn=_to_int)

        rows = conn.execute(
            "SELECT node_id, last_seen_unix FROM node_capabilities ORDER BY node_id ASC"
        ).fetchall()
        assert rows == [("!existing", 50)]
    finally:
        conn.close()
