import time
from typing import Any, Dict, Optional

from .helpers import extract_position_fields as _extract_position_fields
from .history_capability_upsert import (
    build_node_capability_insert_values as _build_node_capability_insert_values,
    merge_node_capability_row as _merge_node_capability_row,
    normalize_node_capability_inputs as _normalize_node_capability_inputs,
)
from .history_metric_rows import (
    build_metric_rollup_values as _build_metric_rollup_values,
    merge_metric_rollup_row as _merge_metric_rollup_row,
)
from .history_packet_events import (
    build_packet_event_insert_values as _build_packet_event_insert_values,
    normalize_packet_event_summary as _normalize_packet_event_summary,
)
from .history_positions import (
    insert_node_position_if_changed as _insert_node_position_if_changed,
)
from .history_rollups import bucket_minute as _bucket_minute


def upsert_node_capability(
    conn: Any,
    *,
    node_id: str,
    event_unix: int,
    has_position: bool,
    last_hops: Optional[int],
    battery_level: Optional[int],
) -> None:
    clean_hops, clean_battery = _normalize_node_capability_inputs(
        last_hops=last_hops,
        battery_level=battery_level,
    )

    row = conn.execute(
        """
        SELECT last_seen_unix, has_position, last_position_unix,
               last_hops, battery_level, battery_updated_unix
        FROM node_capabilities
        WHERE node_id = ?
        """,
        (node_id,),
    ).fetchone()

    if row is None:
        conn.execute(
            """
            INSERT INTO node_capabilities(
              node_id, last_seen_unix, has_position, last_position_unix,
              last_hops, battery_level, battery_updated_unix
            ) VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            _build_node_capability_insert_values(
                node_id=node_id,
                event_unix=event_unix,
                has_position=has_position,
                clean_hops=clean_hops,
                clean_battery=clean_battery,
            ),
        )
        return

    merged = _merge_node_capability_row(
        row=row,
        event_unix=event_unix,
        has_position=has_position,
        clean_hops=clean_hops,
        clean_battery=clean_battery,
    )

    conn.execute(
        """
        UPDATE node_capabilities
        SET last_seen_unix = ?,
            has_position = ?,
            last_position_unix = ?,
            last_hops = ?,
            battery_level = ?,
            battery_updated_unix = ?
        WHERE node_id = ?
        """,
        (
            merged["last_seen_unix"],
            1 if merged["has_position"] else 0,
            merged["last_position_unix"],
            merged["last_hops"],
            merged["battery_level"],
            merged["battery_updated_unix"],
            node_id,
        ),
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


def save_packet_event_and_rollups(
    conn: Any,
    summary: Dict[str, Any],
    *,
    now_unix_fn=time.time,
) -> None:
    normalized = _normalize_packet_event_summary(summary, now_unix_fn=now_unix_fn)
    event_unix = normalized["event_unix"]
    from_id = normalized["from_id"]
    to_id = normalized["to_id"]
    rx_snr = normalized["rx_snr"]
    rx_rssi = normalized["rx_rssi"]
    hops = normalized["hops"]
    position_data = normalized["position_data"]
    battery_level = normalized["battery_level"]

    conn.execute(
        """
        INSERT INTO packet_events(
          created_unix, from_id, to_id, portnum,
          rx_snr, rx_rssi, hops, hop_start, hop_limit,
          channel, want_ack, priority, summary_json
        ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        _build_packet_event_insert_values(normalized),
    )

    bucket_unix = _bucket_minute(event_unix)
    if from_id:
        upsert_node_metric(
            conn,
            bucket_unix=bucket_unix,
            node_id=from_id,
            event_unix=event_unix,
            rx_snr=rx_snr,
            rx_rssi=rx_rssi,
            hops=hops,
        )
        _insert_node_position_if_changed(
            conn,
            node_id=from_id,
            event_unix=event_unix,
            position_data=position_data,
        )
        upsert_node_capability(
            conn,
            node_id=from_id,
            event_unix=event_unix,
            has_position=_extract_position_fields(position_data) is not None,
            last_hops=hops,
            battery_level=battery_level,
        )
    if from_id and to_id and from_id != to_id:
        upsert_link_metric(
            conn,
            bucket_unix=bucket_unix,
            from_id=from_id,
            to_id=to_id,
            event_unix=event_unix,
            rx_snr=rx_snr,
            rx_rssi=rx_rssi,
            hops=hops,
        )
