import json
import os
import sqlite3
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional

from .helpers import (
    extract_position_fields as _extract_position_fields,
    format_epoch as _format_epoch,
    safe_json_loads as _safe_json_loads,
    to_float as _to_float,
    to_int as _to_int,
)
from .history_rollups import (
    bucket_minute as _bucket_minute_helper,
    clean_node_id as _clean_node_id_helper,
    merge_metric as _merge_metric_helper,
)
from .history_readers import (
    decode_connections_rows as _decode_connections_rows_helper,
    decode_recent_chat_rows as _decode_recent_chat_rows_helper,
    decode_recent_packets_rows as _decode_recent_packets_rows_helper,
)
from .history_analytics import (
    build_node_history_payload as _build_node_history_payload_helper,
    build_online_activity_payload as _build_online_activity_payload_helper,
)
from .history_prune import prune_history_tables as _prune_history_tables_helper
from .history_schema import initialize_history_schema as _initialize_history_schema_helper


class HistoryStore:
    def __init__(
        self,
        db_path: str,
        max_rows: int,
        retention_days: int,
        event_max_rows: int,
        event_retention_days: int,
        rollup_retention_days: int,
    ) -> None:
        self.db_path = db_path
        self.max_rows = max(100, int(max_rows))
        self.retention_seconds = max(0, int(retention_days)) * 86400
        self.event_max_rows = max(1000, int(event_max_rows))
        self.event_retention_seconds = max(0, int(event_retention_days)) * 86400
        self.rollup_retention_seconds = max(0, int(rollup_retention_days)) * 86400
        self._writes_since_prune = 0
        self._lock = threading.Lock()

        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA busy_timeout=5000")

        with self._lock:
            self._init_schema_unlocked()
            self._prune_unlocked()
            self._maybe_backfill_node_capabilities_unlocked()
            self._conn.commit()

    def _init_schema_unlocked(self) -> None:
        _initialize_history_schema_helper(self._conn)

    def _maybe_backfill_node_capabilities_unlocked(self) -> None:
        existing = self._conn.execute("SELECT COUNT(*) FROM node_capabilities").fetchone()
        if existing and int(existing[0] or 0) > 0:
            return

        merged: Dict[str, Dict[str, Any]] = {}

        metric_rows = self._conn.execute(
            """
            SELECT node_id, MAX(last_seen_unix)
            FROM node_metrics_1m
            GROUP BY node_id
            """
        ).fetchall()
        for node_id, last_seen_unix in metric_rows:
            clean_node_id = str(node_id or "").strip()
            seen = _to_int(last_seen_unix)
            if not clean_node_id or seen is None:
                continue
            merged.setdefault(clean_node_id, {})
            merged[clean_node_id]["last_seen_unix"] = seen

        position_rows = self._conn.execute(
            """
            SELECT node_id, MAX(created_unix)
            FROM node_positions
            GROUP BY node_id
            """
        ).fetchall()
        for node_id, last_position_unix in position_rows:
            clean_node_id = str(node_id or "").strip()
            pos_unix = _to_int(last_position_unix)
            if not clean_node_id or pos_unix is None:
                continue
            node = merged.setdefault(clean_node_id, {})
            node["has_position"] = True
            node["last_position_unix"] = pos_unix
            node["last_seen_unix"] = max(_to_int(node.get("last_seen_unix")) or pos_unix, pos_unix)

        hop_rows = self._conn.execute(
            """
            SELECT events.from_id, events.hops, events.created_unix
            FROM packet_events AS events
            JOIN (
              SELECT from_id, MAX(id) AS max_id
              FROM packet_events
              WHERE from_id IS NOT NULL AND hops IS NOT NULL
              GROUP BY from_id
            ) AS latest
              ON latest.from_id = events.from_id AND latest.max_id = events.id
            """
        ).fetchall()
        for node_id, last_hops, hop_seen_unix in hop_rows:
            clean_node_id = str(node_id or "").strip()
            hops = _to_int(last_hops)
            seen = _to_int(hop_seen_unix)
            if not clean_node_id:
                continue
            node = merged.setdefault(clean_node_id, {})
            if hops is not None and hops >= 0:
                node["last_hops"] = hops
            if seen is not None:
                node["last_seen_unix"] = max(_to_int(node.get("last_seen_unix")) or seen, seen)

        for node_id, values in merged.items():
            seen = _to_int(values.get("last_seen_unix"))
            if seen is None or seen <= 0:
                continue
            has_position = 1 if values.get("has_position") else 0
            self._conn.execute(
                """
                INSERT OR REPLACE INTO node_capabilities(
                  node_id, last_seen_unix, has_position, last_position_unix,
                  last_hops, battery_level, battery_updated_unix
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node_id,
                    seen,
                    has_position,
                    _to_int(values.get("last_position_unix")),
                    _to_int(values.get("last_hops")),
                    None,
                    None,
                ),
            )

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _prune_unlocked(self) -> None:
        _prune_history_tables_helper(
            self._conn,
            now_unix=int(time.time()),
            retention_seconds=self.retention_seconds,
            event_retention_seconds=self.event_retention_seconds,
            rollup_retention_seconds=self.rollup_retention_seconds,
            max_rows=self.max_rows,
            event_max_rows=self.event_max_rows,
        )

    def _maybe_prune_unlocked(self) -> None:
        self._writes_since_prune += 1
        if self._writes_since_prune < 50:
            return
        self._writes_since_prune = 0
        self._prune_unlocked()

    def load_recent_packets(self, limit: int) -> list[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT summary_json, packet_json FROM packets ORDER BY id DESC LIMIT ?",
                (max(1, int(limit)),),
            ).fetchall()
        return _decode_recent_packets_rows_helper(rows)

    def load_recent_chat(self, limit: int) -> list[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT message_json FROM chat ORDER BY id DESC LIMIT ?",
                (max(1, int(limit)),),
            ).fetchall()
        return _decode_recent_chat_rows_helper(rows)

    def load_connections(self) -> list[Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT from_id, to_id, first_seen_unix, last_seen_unix, seen_count,
                       portnums_json, last_hops, hops_sum, hops_count
                FROM connections
                ORDER BY last_seen_unix DESC
                """
            ).fetchall()
        return _decode_connections_rows_helper(rows)

    def load_node_history(self, node_id: str, window_hours: int, max_points: int) -> Dict[str, Any]:
        clean_node_id = str(node_id or "").strip()
        hours = max(1, int(window_hours))
        if not clean_node_id:
            return _build_node_history_payload_helper(
                node_id="",
                window_hours=hours,
                metric_rows=[],
                position_rows=[],
            )
        limit = max(20, min(10000, int(max_points)))
        cutoff = int(time.time()) - (hours * 3600)

        with self._lock:
            rows = self._conn.execute(
                """
                SELECT bucket_unix, packet_count,
                       snr_sum, snr_count, snr_min, snr_max,
                       rssi_sum, rssi_count, rssi_min, rssi_max,
                       hops_sum, hops_count, hops_min, hops_max,
                       last_seen_unix
                FROM node_metrics_1m
                WHERE node_id = ? AND bucket_unix >= ?
                ORDER BY bucket_unix DESC
                LIMIT ?
                """,
                (clean_node_id, cutoff, limit),
            ).fetchall()
            position_rows = self._conn.execute(
                """
                SELECT created_unix, lat, lon, altitude, sats_in_view
                FROM node_positions
                WHERE node_id = ? AND created_unix >= ?
                ORDER BY created_unix DESC
                LIMIT ?
                """,
                (clean_node_id, cutoff, limit),
            ).fetchall()

        return _build_node_history_payload_helper(
            node_id=clean_node_id,
            window_hours=hours,
            metric_rows=rows,
            position_rows=position_rows,
        )

    def load_online_activity(self, window_hours: int) -> Dict[str, Any]:
        hours = max(1, min(24 * 365, int(window_hours)))
        cutoff = int(time.time()) - (hours * 3600)

        with self._lock:
            rows = self._conn.execute(
                """
                SELECT bucket_unix - (bucket_unix % 3600) AS hour_bucket,
                       COUNT(DISTINCT node_id) AS online_nodes
                FROM node_metrics_1m
                WHERE bucket_unix >= ?
                GROUP BY hour_bucket
                ORDER BY hour_bucket ASC
                """,
                (cutoff,),
            ).fetchall()
            distinct_row = self._conn.execute(
                "SELECT COUNT(DISTINCT node_id) FROM node_metrics_1m WHERE bucket_unix >= ?",
                (cutoff,),
            ).fetchone()

        return _build_online_activity_payload_helper(
            window_hours=hours,
            hour_rows=rows,
            distinct_nodes=int((distinct_row[0] if distinct_row else 0) or 0),
            timezone_label=datetime.now().astimezone().tzname() or "local",
        )

    def load_node_saved_counts(self) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT node_id,
                       SUM(packet_count) AS saved_packets,
                       COUNT(*) AS saved_points,
                       MAX(last_seen_unix) AS saved_last_seen_unix
                FROM node_metrics_1m
                GROUP BY node_id
                """
            ).fetchall()

        for node_id, saved_packets, saved_points, saved_last_seen_unix in rows:
            clean_node_id = str(node_id or "").strip()
            if not clean_node_id:
                continue
            out[clean_node_id] = {
                "saved_packets": int(saved_packets or 0),
                "saved_points": int(saved_points or 0),
                "saved_last_seen": _format_epoch(saved_last_seen_unix),
            }
        return out

    def load_node_capabilities(self) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT node_id, last_seen_unix, has_position, last_position_unix,
                       last_hops, battery_level, battery_updated_unix
                FROM node_capabilities
                ORDER BY last_seen_unix DESC
                """
            ).fetchall()

        for (
            node_id,
            last_seen_unix,
            has_position,
            last_position_unix,
            last_hops,
            battery_level,
            battery_updated_unix,
        ) in rows:
            clean_node_id = str(node_id or "").strip()
            if not clean_node_id:
                continue
            out[clean_node_id] = {
                "last_seen_unix": _to_int(last_seen_unix),
                "last_seen": _format_epoch(last_seen_unix),
                "has_position": bool(_to_int(has_position)),
                "last_position_unix": _to_int(last_position_unix),
                "last_position_time": _format_epoch(last_position_unix),
                "last_hops": _to_int(last_hops),
                "battery_level": _to_int(battery_level),
                "battery_updated_unix": _to_int(battery_updated_unix),
                "battery_updated_time": _format_epoch(battery_updated_unix),
            }
        return out

    def save_connection_event(
        self,
        from_id: str,
        to_id: str,
        rx_time: Optional[int],
        portnum: Optional[str],
        hops: Optional[int],
    ) -> None:
        event_unix = rx_time if isinstance(rx_time, int) and rx_time > 0 else int(time.time())
        clean_port = str(portnum) if portnum is not None else None
        clean_hops = hops if isinstance(hops, int) and hops >= 0 else None

        with self._lock:
            row = self._conn.execute(
                """
                SELECT first_seen_unix, last_seen_unix, seen_count, portnums_json, last_hops, hops_sum, hops_count
                FROM connections
                WHERE from_id = ? AND to_id = ?
                """,
                (from_id, to_id),
            ).fetchone()

            if row is None:
                ports: set[str] = set()
                if clean_port:
                    ports.add(clean_port)
                self._conn.execute(
                    """
                    INSERT INTO connections(
                      from_id, to_id, first_seen_unix, last_seen_unix, seen_count,
                      portnums_json, last_hops, hops_sum, hops_count
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        from_id,
                        to_id,
                        event_unix,
                        event_unix,
                        1,
                        json.dumps(sorted(ports), separators=(",", ":")),
                        clean_hops,
                        clean_hops if clean_hops is not None else 0,
                        1 if clean_hops is not None else 0,
                    ),
                )
            else:
                first_seen_unix, last_seen_unix, seen_count, portnums_json, last_hops, hops_sum, hops_count = row
                ports = _safe_json_loads(portnums_json, [])
                if not isinstance(ports, list):
                    ports = []
                port_set = {str(p) for p in ports if p is not None}
                if clean_port:
                    port_set.add(clean_port)

                merged_first = min(_to_int(first_seen_unix) or event_unix, event_unix)
                merged_last = max(_to_int(last_seen_unix) or event_unix, event_unix)
                merged_count = (_to_int(seen_count) or 0) + 1

                merged_hops_sum = _to_int(hops_sum) or 0
                merged_hops_count = _to_int(hops_count) or 0
                merged_last_hops = _to_int(last_hops)
                if clean_hops is not None:
                    merged_hops_sum += clean_hops
                    merged_hops_count += 1
                    merged_last_hops = clean_hops

                self._conn.execute(
                    """
                    UPDATE connections
                    SET first_seen_unix = ?, last_seen_unix = ?, seen_count = ?,
                        portnums_json = ?, last_hops = ?, hops_sum = ?, hops_count = ?
                    WHERE from_id = ? AND to_id = ?
                    """,
                    (
                        merged_first,
                        merged_last,
                        merged_count,
                        json.dumps(sorted(port_set), separators=(",", ":")),
                        merged_last_hops,
                        merged_hops_sum,
                        merged_hops_count,
                        from_id,
                        to_id,
                    ),
                )

            self._maybe_prune_unlocked()
            self._conn.commit()

    def _save_node_position_unlocked(self, node_id: str, event_unix: int, position_data: Any) -> None:
        coords = _extract_position_fields(position_data)
        if coords is None:
            return

        altitude: Optional[float] = None
        sats: Optional[int] = None
        if isinstance(position_data, dict):
            altitude = _to_float(position_data.get("altitude"))
            if altitude is None:
                altitude = _to_float(position_data.get("altitude_m"))
            if altitude is None:
                altitude = _to_float(position_data.get("altitudeM"))

            sats = _to_int(position_data.get("sats_in_view"))
            if sats is None:
                sats = _to_int(position_data.get("satsInView"))
            if sats is None:
                sats = _to_int(position_data.get("satellites"))

        latest = self._conn.execute(
            """
            SELECT created_unix, lat, lon
            FROM node_positions
            WHERE node_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (node_id,),
        ).fetchone()
        if latest is not None:
            latest_unix, latest_lat, latest_lon = latest
            latest_unix_i = _to_int(latest_unix)
            latest_lat_f = _to_float(latest_lat)
            latest_lon_f = _to_float(latest_lon)
            if (
                latest_unix_i is not None
                and latest_lat_f is not None
                and latest_lon_f is not None
                and abs(coords[0] - latest_lat_f) < 1e-7
                and abs(coords[1] - latest_lon_f) < 1e-7
                and abs(event_unix - latest_unix_i) < 30
            ):
                return

        self._conn.execute(
            """
            INSERT INTO node_positions(created_unix, node_id, lat, lon, altitude, sats_in_view)
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (
                event_unix,
                node_id,
                coords[0],
                coords[1],
                altitude,
                sats if sats is not None and sats >= 0 else None,
            ),
        )

    def _upsert_node_capability_unlocked(
        self,
        node_id: str,
        event_unix: int,
        has_position: bool,
        last_hops: Optional[int],
        battery_level: Optional[int],
    ) -> None:
        clean_hops = last_hops if isinstance(last_hops, int) and last_hops >= 0 else None
        clean_battery = battery_level if isinstance(battery_level, int) and 0 <= battery_level <= 100 else None

        row = self._conn.execute(
            """
            SELECT last_seen_unix, has_position, last_position_unix,
                   last_hops, battery_level, battery_updated_unix
            FROM node_capabilities
            WHERE node_id = ?
            """,
            (node_id,),
        ).fetchone()

        if row is None:
            self._conn.execute(
                """
                INSERT INTO node_capabilities(
                  node_id, last_seen_unix, has_position, last_position_unix,
                  last_hops, battery_level, battery_updated_unix
                ) VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    node_id,
                    event_unix,
                    1 if has_position else 0,
                    event_unix if has_position else None,
                    clean_hops,
                    clean_battery,
                    event_unix if clean_battery is not None else None,
                ),
            )
            return

        (
            last_seen_unix,
            row_has_position,
            row_last_position_unix,
            row_last_hops,
            row_battery_level,
            row_battery_updated_unix,
        ) = row
        merged_last_seen = max(_to_int(last_seen_unix) or event_unix, event_unix)
        merged_has_position = bool(_to_int(row_has_position)) or has_position
        merged_last_position_unix = _to_int(row_last_position_unix)
        if has_position:
            merged_last_position_unix = event_unix

        merged_last_hops = clean_hops if clean_hops is not None else _to_int(row_last_hops)
        merged_battery_level = _to_int(row_battery_level)
        merged_battery_updated_unix = _to_int(row_battery_updated_unix)
        if clean_battery is not None:
            merged_battery_level = clean_battery
            merged_battery_updated_unix = event_unix

        self._conn.execute(
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
                merged_last_seen,
                1 if merged_has_position else 0,
                merged_last_position_unix,
                merged_last_hops,
                merged_battery_level,
                merged_battery_updated_unix,
                node_id,
            ),
        )

    def _upsert_node_metric_unlocked(
        self,
        bucket_unix: int,
        node_id: str,
        event_unix: int,
        rx_snr: Optional[float],
        rx_rssi: Optional[float],
        hops: Optional[int],
    ) -> None:
        row = self._conn.execute(
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
            snr_sum, snr_count, snr_min, snr_max = _merge_metric_helper(0.0, 0, None, None, rx_snr)
            rssi_sum, rssi_count, rssi_min, rssi_max = _merge_metric_helper(0.0, 0, None, None, rx_rssi)
            hops_sum, hops_count, hops_min, hops_max = _merge_metric_helper(
                0.0,
                0,
                None,
                None,
                float(hops) if hops is not None else None,
            )
            self._conn.execute(
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
                    1,
                    snr_sum,
                    snr_count,
                    snr_min,
                    snr_max,
                    rssi_sum,
                    rssi_count,
                    rssi_min,
                    rssi_max,
                    int(hops_sum),
                    hops_count,
                    int(hops_min) if hops_min is not None else None,
                    int(hops_max) if hops_max is not None else None,
                    event_unix,
                ),
            )
            return

        (
            packet_count,
            snr_sum,
            snr_count,
            snr_min,
            snr_max,
            rssi_sum,
            rssi_count,
            rssi_min,
            rssi_max,
            hops_sum,
            hops_count,
            hops_min,
            hops_max,
            last_seen_unix,
        ) = row

        snr_sum, snr_count, snr_min, snr_max = _merge_metric_helper(
            snr_sum, snr_count, snr_min, snr_max, rx_snr
        )
        rssi_sum, rssi_count, rssi_min, rssi_max = _merge_metric_helper(
            rssi_sum,
            rssi_count,
            rssi_min,
            rssi_max,
            rx_rssi,
        )
        hops_sum_f, hops_count, hops_min_f, hops_max_f = _merge_metric_helper(
            hops_sum,
            hops_count,
            hops_min,
            hops_max,
            float(hops) if hops is not None else None,
        )

        self._conn.execute(
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
                int(packet_count or 0) + 1,
                snr_sum,
                snr_count,
                snr_min,
                snr_max,
                rssi_sum,
                rssi_count,
                rssi_min,
                rssi_max,
                int(hops_sum_f),
                hops_count,
                int(hops_min_f) if hops_min_f is not None else None,
                int(hops_max_f) if hops_max_f is not None else None,
                max(_to_int(last_seen_unix) or event_unix, event_unix),
                bucket_unix,
                node_id,
            ),
        )

    def _upsert_link_metric_unlocked(
        self,
        bucket_unix: int,
        from_id: str,
        to_id: str,
        event_unix: int,
        rx_snr: Optional[float],
        rx_rssi: Optional[float],
        hops: Optional[int],
    ) -> None:
        row = self._conn.execute(
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
            snr_sum, snr_count, snr_min, snr_max = _merge_metric_helper(0.0, 0, None, None, rx_snr)
            rssi_sum, rssi_count, rssi_min, rssi_max = _merge_metric_helper(0.0, 0, None, None, rx_rssi)
            hops_sum, hops_count, hops_min, hops_max = _merge_metric_helper(
                0.0,
                0,
                None,
                None,
                float(hops) if hops is not None else None,
            )
            self._conn.execute(
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
                    1,
                    snr_sum,
                    snr_count,
                    snr_min,
                    snr_max,
                    rssi_sum,
                    rssi_count,
                    rssi_min,
                    rssi_max,
                    int(hops_sum),
                    hops_count,
                    int(hops_min) if hops_min is not None else None,
                    int(hops_max) if hops_max is not None else None,
                    event_unix,
                ),
            )
            return

        (
            packet_count,
            snr_sum,
            snr_count,
            snr_min,
            snr_max,
            rssi_sum,
            rssi_count,
            rssi_min,
            rssi_max,
            hops_sum,
            hops_count,
            hops_min,
            hops_max,
            last_seen_unix,
        ) = row

        snr_sum, snr_count, snr_min, snr_max = _merge_metric_helper(
            snr_sum, snr_count, snr_min, snr_max, rx_snr
        )
        rssi_sum, rssi_count, rssi_min, rssi_max = _merge_metric_helper(
            rssi_sum,
            rssi_count,
            rssi_min,
            rssi_max,
            rx_rssi,
        )
        hops_sum_f, hops_count, hops_min_f, hops_max_f = _merge_metric_helper(
            hops_sum,
            hops_count,
            hops_min,
            hops_max,
            float(hops) if hops is not None else None,
        )

        self._conn.execute(
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
                int(packet_count or 0) + 1,
                snr_sum,
                snr_count,
                snr_min,
                snr_max,
                rssi_sum,
                rssi_count,
                rssi_min,
                rssi_max,
                int(hops_sum_f),
                hops_count,
                int(hops_min_f) if hops_min_f is not None else None,
                int(hops_max_f) if hops_max_f is not None else None,
                max(_to_int(last_seen_unix) or event_unix, event_unix),
                bucket_unix,
                from_id,
                to_id,
            ),
        )

    def _save_packet_event_and_rollups_unlocked(self, summary: Dict[str, Any]) -> None:
        event_unix = _to_int(summary.get("rx_time_unix"))
        if event_unix is None or event_unix <= 0:
            event_unix = int(time.time())

        from_id = _clean_node_id_helper(summary.get("from"))
        to_id = _clean_node_id_helper(summary.get("to"))
        portnum_raw = summary.get("portnum")
        portnum = str(portnum_raw) if portnum_raw is not None else None
        rx_snr = _to_float(summary.get("rx_snr"))
        rx_rssi = _to_float(summary.get("rx_rssi"))
        hops = _to_int(summary.get("hops"))
        hop_start = _to_int(summary.get("hop_start"))
        hop_limit = _to_int(summary.get("hop_limit"))
        channel_raw = summary.get("channel")
        channel = str(channel_raw) if channel_raw is not None else None
        priority_raw = summary.get("priority")
        priority = str(priority_raw) if priority_raw is not None else None
        want_ack = 1 if summary.get("want_ack") else 0
        position_data = summary.get("position")
        battery_level = _to_int(summary.get("battery_level"))

        self._conn.execute(
            """
            INSERT INTO packet_events(
              created_unix, from_id, to_id, portnum,
              rx_snr, rx_rssi, hops, hop_start, hop_limit,
              channel, want_ack, priority, summary_json
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_unix,
                from_id,
                to_id,
                portnum,
                rx_snr,
                rx_rssi,
                hops,
                hop_start,
                hop_limit,
                channel,
                want_ack,
                priority,
                json.dumps(summary, separators=(",", ":")),
            ),
        )

        bucket_unix = _bucket_minute_helper(event_unix)
        if from_id:
            self._upsert_node_metric_unlocked(
                bucket_unix=bucket_unix,
                node_id=from_id,
                event_unix=event_unix,
                rx_snr=rx_snr,
                rx_rssi=rx_rssi,
                hops=hops,
            )
            self._save_node_position_unlocked(
                node_id=from_id,
                event_unix=event_unix,
                position_data=position_data,
            )
            self._upsert_node_capability_unlocked(
                node_id=from_id,
                event_unix=event_unix,
                has_position=_extract_position_fields(position_data) is not None,
                last_hops=hops,
                battery_level=battery_level,
            )
        if from_id and to_id and from_id != to_id:
            self._upsert_link_metric_unlocked(
                bucket_unix=bucket_unix,
                from_id=from_id,
                to_id=to_id,
                event_unix=event_unix,
                rx_snr=rx_snr,
                rx_rssi=rx_rssi,
                hops=hops,
            )

    def save_packet(self, packet_entry: Dict[str, Any]) -> None:
        summary = packet_entry.get("summary")
        packet = packet_entry.get("packet")
        summary_json = json.dumps(summary, separators=(",", ":"))
        packet_json = json.dumps(packet, separators=(",", ":"))

        with self._lock:
            self._conn.execute(
                "INSERT INTO packets(created_unix, summary_json, packet_json) VALUES(?, ?, ?)",
                (int(time.time()), summary_json, packet_json),
            )
            if isinstance(summary, dict):
                self._save_packet_event_and_rollups_unlocked(summary)
            self._maybe_prune_unlocked()
            self._conn.commit()

    def save_chat(self, chat_entry: Dict[str, Any]) -> None:
        message_json = json.dumps(chat_entry, separators=(",", ":"))

        with self._lock:
            self._conn.execute(
                "INSERT INTO chat(created_unix, message_json) VALUES(?, ?)",
                (int(time.time()), message_json),
            )
            self._maybe_prune_unlocked()
            self._conn.commit()
