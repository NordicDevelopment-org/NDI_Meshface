from typing import Any, Optional

from .history_metric_rows import (
    build_metric_rollup_values as _build_metric_rollup_values,
    merge_metric_rollup_row as _merge_metric_rollup_row,
)


def upsert_node_metric(
    conn: Any,
    *,
    bucket_unix: int,
    node_id: str,
    event_unix: int,
    rx_snr: Optional[float],
    rx_rssi: Optional[float],
    hops: Optional[int],
) -> None:
    row = conn.execute(
        """
        SELECT packet_count,
               snr_sum, snr_count, snr_min, snr_max,
               rssi_sum, rssi_count, rssi_min, rssi_max,
               hops_sum, hops_count, hops_min, hops_max,
               last_seen_unix
        FROM node_metrics_1m
        WHERE bucket_unix = ? AND node_id = ?
        """,
        (bucket_unix, node_id),
    ).fetchone()

    if row is None:
        rolled = _build_metric_rollup_values(
            event_unix=event_unix,
            rx_snr=rx_snr,
            rx_rssi=rx_rssi,
            hops=hops,
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
            (
                bucket_unix,
                node_id,
                rolled["packet_count"],
                rolled["snr_sum"],
                rolled["snr_count"],
                rolled["snr_min"],
                rolled["snr_max"],
                rolled["rssi_sum"],
                rolled["rssi_count"],
                rolled["rssi_min"],
                rolled["rssi_max"],
                rolled["hops_sum"],
                rolled["hops_count"],
                rolled["hops_min"],
                rolled["hops_max"],
                rolled["last_seen_unix"],
            ),
        )
        return

    merged = _merge_metric_rollup_row(
        row=row,
        event_unix=event_unix,
        rx_snr=rx_snr,
        rx_rssi=rx_rssi,
        hops=hops,
    )
    conn.execute(
        """
        UPDATE node_metrics_1m
        SET packet_count = ?,
            snr_sum = ?, snr_count = ?, snr_min = ?, snr_max = ?,
            rssi_sum = ?, rssi_count = ?, rssi_min = ?, rssi_max = ?,
            hops_sum = ?, hops_count = ?, hops_min = ?, hops_max = ?,
            last_seen_unix = ?
        WHERE bucket_unix = ? AND node_id = ?
        """,
        (
            merged["packet_count"],
            merged["snr_sum"],
            merged["snr_count"],
            merged["snr_min"],
            merged["snr_max"],
            merged["rssi_sum"],
            merged["rssi_count"],
            merged["rssi_min"],
            merged["rssi_max"],
            merged["hops_sum"],
            merged["hops_count"],
            merged["hops_min"],
            merged["hops_max"],
            merged["last_seen_unix"],
            bucket_unix,
            node_id,
        ),
    )


def upsert_link_metric(
    conn: Any,
    *,
    bucket_unix: int,
    from_id: str,
    to_id: str,
    event_unix: int,
    rx_snr: Optional[float],
    rx_rssi: Optional[float],
    hops: Optional[int],
) -> None:
    row = conn.execute(
        """
        SELECT packet_count,
               snr_sum, snr_count, snr_min, snr_max,
               rssi_sum, rssi_count, rssi_min, rssi_max,
               hops_sum, hops_count, hops_min, hops_max,
               last_seen_unix
        FROM link_metrics_1m
        WHERE bucket_unix = ? AND from_id = ? AND to_id = ?
        """,
        (bucket_unix, from_id, to_id),
    ).fetchone()

    if row is None:
        rolled = _build_metric_rollup_values(
            event_unix=event_unix,
            rx_snr=rx_snr,
            rx_rssi=rx_rssi,
            hops=hops,
        )
        conn.execute(
            """
            INSERT INTO link_metrics_1m(
              bucket_unix, from_id, to_id, packet_count,
              snr_sum, snr_count, snr_min, snr_max,
              rssi_sum, rssi_count, rssi_min, rssi_max,
              hops_sum, hops_count, hops_min, hops_max,
              last_seen_unix
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                bucket_unix,
                from_id,
                to_id,
                rolled["packet_count"],
                rolled["snr_sum"],
                rolled["snr_count"],
                rolled["snr_min"],
                rolled["snr_max"],
                rolled["rssi_sum"],
                rolled["rssi_count"],
                rolled["rssi_min"],
                rolled["rssi_max"],
                rolled["hops_sum"],
                rolled["hops_count"],
                rolled["hops_min"],
                rolled["hops_max"],
                rolled["last_seen_unix"],
            ),
        )
        return

    merged = _merge_metric_rollup_row(
        row=row,
        event_unix=event_unix,
        rx_snr=rx_snr,
        rx_rssi=rx_rssi,
        hops=hops,
    )
    conn.execute(
        """
        UPDATE link_metrics_1m
        SET packet_count = ?,
            snr_sum = ?, snr_count = ?, snr_min = ?, snr_max = ?,
            rssi_sum = ?, rssi_count = ?, rssi_min = ?, rssi_max = ?,
            hops_sum = ?, hops_count = ?, hops_min = ?, hops_max = ?,
            last_seen_unix = ?
        WHERE bucket_unix = ? AND from_id = ? AND to_id = ?
        """,
        (
            merged["packet_count"],
            merged["snr_sum"],
            merged["snr_count"],
            merged["snr_min"],
            merged["snr_max"],
            merged["rssi_sum"],
            merged["rssi_count"],
            merged["rssi_min"],
            merged["rssi_max"],
            merged["hops_sum"],
            merged["hops_count"],
            merged["hops_min"],
            merged["hops_max"],
            merged["last_seen_unix"],
            bucket_unix,
            from_id,
            to_id,
        ),
    )
