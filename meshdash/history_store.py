import json
import os
import sqlite3
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional

from .helpers import to_int as _to_int
from .history_readers import (
    decode_connections_rows as _decode_connections_rows_helper,
    decode_recent_chat_rows as _decode_recent_chat_rows_helper,
    decode_recent_packets_rows as _decode_recent_packets_rows_helper,
)
from .history_analytics import (
    build_node_history_payload as _build_node_history_payload_helper,
    build_online_activity_payload as _build_online_activity_payload_helper,
)
from .history_connections import (
    build_connection_insert_values as _build_connection_insert_values_helper,
    merge_connection_row as _merge_connection_row_helper,
    normalize_connection_event_input as _normalize_connection_event_input_helper,
)
from .history_capabilities import (
    decode_node_capabilities_rows as _decode_node_capabilities_rows_helper,
    decode_node_saved_counts_rows as _decode_node_saved_counts_rows_helper,
)
from .history_backfill import backfill_node_capabilities as _backfill_node_capabilities_helper
from .history_writes import (
    save_packet_event_and_rollups as _save_packet_event_and_rollups_helper,
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
        _backfill_node_capabilities_helper(self._conn, to_int_fn=_to_int)

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
        return _decode_node_saved_counts_rows_helper(rows)

    def load_node_capabilities(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT node_id, last_seen_unix, has_position, last_position_unix,
                       last_hops, battery_level, battery_updated_unix
                FROM node_capabilities
                ORDER BY last_seen_unix DESC
                """
            ).fetchall()
        return _decode_node_capabilities_rows_helper(rows)

    def save_connection_event(
        self,
        from_id: str,
        to_id: str,
        rx_time: Optional[int],
        portnum: Optional[str],
        hops: Optional[int],
    ) -> None:
        event_unix, clean_port, clean_hops = _normalize_connection_event_input_helper(
            rx_time=rx_time,
            portnum=portnum,
            hops=hops,
        )

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
                self._conn.execute(
                    """
                    INSERT INTO connections(
                      from_id, to_id, first_seen_unix, last_seen_unix, seen_count,
                      portnums_json, last_hops, hops_sum, hops_count
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    _build_connection_insert_values_helper(
                        from_id=from_id,
                        to_id=to_id,
                        event_unix=event_unix,
                        clean_port=clean_port,
                        clean_hops=clean_hops,
                    ),
                )
            else:
                merged = _merge_connection_row_helper(
                    row=row,
                    event_unix=event_unix,
                    clean_port=clean_port,
                    clean_hops=clean_hops,
                )

                self._conn.execute(
                    """
                    UPDATE connections
                    SET first_seen_unix = ?, last_seen_unix = ?, seen_count = ?,
                        portnums_json = ?, last_hops = ?, hops_sum = ?, hops_count = ?
                    WHERE from_id = ? AND to_id = ?
                    """,
                    (
                        merged["first_seen_unix"],
                        merged["last_seen_unix"],
                        merged["seen_count"],
                        merged["portnums_json"],
                        merged["last_hops"],
                        merged["hops_sum"],
                        merged["hops_count"],
                        from_id,
                        to_id,
                    ),
                )

            self._maybe_prune_unlocked()
            self._conn.commit()

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
                _save_packet_event_and_rollups_helper(self._conn, summary, now_unix_fn=time.time)
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
