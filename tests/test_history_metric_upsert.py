import sqlite3

from meshdash.history_metric_rows import build_metric_rollup_values, merge_metric_rollup_row
from meshdash.history_metric_upsert import upsert_metric_rollup_row
from meshdash.history.db import initialize_history_schema


def test_upsert_metric_rollup_row_handles_node_metric_insert_and_merge():
    conn = sqlite3.connect(":memory:")
    try:
        initialize_history_schema(conn)
        upsert_metric_rollup_row(
            conn,
            table_name="node_metrics_1m",
            key_fields=("node_id",),
            key_values=("!n1",),
            bucket_unix=60,
            event_unix=60,
            rx_snr=2.0,
            rx_rssi=-101.0,
            hops=1,
            build_metric_rollup_values_fn=build_metric_rollup_values,
            merge_metric_rollup_row_fn=merge_metric_rollup_row,
        )
        upsert_metric_rollup_row(
            conn,
            table_name="node_metrics_1m",
            key_fields=("node_id",),
            key_values=("!n1",),
            bucket_unix=60,
            event_unix=85,
            rx_snr=4.0,
            rx_rssi=-99.0,
            hops=2,
            build_metric_rollup_values_fn=build_metric_rollup_values,
            merge_metric_rollup_row_fn=merge_metric_rollup_row,
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


def test_upsert_metric_rollup_row_handles_link_metric_insert_and_merge():
    conn = sqlite3.connect(":memory:")
    try:
        initialize_history_schema(conn)
        upsert_metric_rollup_row(
            conn,
            table_name="link_metrics_1m",
            key_fields=("from_id", "to_id"),
            key_values=("!n1", "!n2"),
            bucket_unix=60,
            event_unix=60,
            rx_snr=2.0,
            rx_rssi=-101.0,
            hops=1,
            build_metric_rollup_values_fn=build_metric_rollup_values,
            merge_metric_rollup_row_fn=merge_metric_rollup_row,
        )
        upsert_metric_rollup_row(
            conn,
            table_name="link_metrics_1m",
            key_fields=("from_id", "to_id"),
            key_values=("!n1", "!n2"),
            bucket_unix=60,
            event_unix=85,
            rx_snr=4.0,
            rx_rssi=-99.0,
            hops=2,
            build_metric_rollup_values_fn=build_metric_rollup_values,
            merge_metric_rollup_row_fn=merge_metric_rollup_row,
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
