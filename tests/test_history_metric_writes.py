import sqlite3

from meshdash.history_metric_writes import upsert_link_metric, upsert_node_metric
from meshdash.history_schema import initialize_history_schema


def test_upsert_node_metric_inserts_and_merges_existing_bucket():
    conn = sqlite3.connect(":memory:")
    try:
        initialize_history_schema(conn)
        upsert_node_metric(
            conn,
            bucket_unix=60,
            node_id="!n1",
            event_unix=60,
            rx_snr=2.0,
            rx_rssi=-101.0,
            hops=1,
        )
        upsert_node_metric(
            conn,
            bucket_unix=60,
            node_id="!n1",
            event_unix=85,
            rx_snr=4.0,
            rx_rssi=-99.0,
            hops=2,
        )

        row = conn.execute(
            """
            SELECT packet_count, snr_count, snr_min, snr_max,
                   rssi_count, rssi_min, rssi_max,
                   hops_count, hops_min, hops_max, last_seen_unix
            FROM node_metrics_1m
            WHERE bucket_unix = ? AND node_id = ?
            """,
            (60, "!n1"),
        ).fetchone()

        assert row == (2, 2, 2.0, 4.0, 2, -101.0, -99.0, 2, 1, 2, 85)
    finally:
        conn.close()


def test_upsert_link_metric_inserts_and_merges_existing_bucket():
    conn = sqlite3.connect(":memory:")
    try:
        initialize_history_schema(conn)
        upsert_link_metric(
            conn,
            bucket_unix=60,
            from_id="!n1",
            to_id="!n2",
            event_unix=60,
            rx_snr=2.0,
            rx_rssi=-101.0,
            hops=1,
        )
        upsert_link_metric(
            conn,
            bucket_unix=60,
            from_id="!n1",
            to_id="!n2",
            event_unix=85,
            rx_snr=4.0,
            rx_rssi=-99.0,
            hops=2,
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

        assert row == (2, 2, 2.0, 4.0, 2, -101.0, -99.0, 2, 1, 2, 85)
    finally:
        conn.close()
