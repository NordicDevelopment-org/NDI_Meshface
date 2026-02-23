import os
import sqlite3
import threading
import time
from typing import Any, Dict, Optional

from .helpers import to_int as _to_int
from .history_readers import (
    decode_connections_rows as _decode_connections_rows_helper,
    decode_recent_chat_rows as _decode_recent_chat_rows_helper,
    decode_recent_packets_rows as _decode_recent_packets_rows_helper,
)
from .history_queries import (
    fetch_connection_rows as _fetch_connection_rows_helper,
    fetch_node_capability_rows as _fetch_node_capability_rows_helper,
    fetch_node_history_rows as _fetch_node_history_rows_helper,
    fetch_node_saved_count_rows as _fetch_node_saved_count_rows_helper,
    fetch_online_activity_rows as _fetch_online_activity_rows_helper,
    fetch_recent_chat_rows as _fetch_recent_chat_rows_helper,
    fetch_recent_packet_rows as _fetch_recent_packet_rows_helper,
)
from .history_analytics import (
    build_node_history_payload as _build_node_history_payload_helper,
    build_online_activity_payload as _build_online_activity_payload_helper,
)
from .history_capabilities import (
    decode_node_capabilities_rows as _decode_node_capabilities_rows_helper,
    decode_node_saved_counts_rows as _decode_node_saved_counts_rows_helper,
)
from .history_connection_writes import (
    save_connection_event as _save_connection_event_helper,
)
from .history_raw_writes import (
    save_chat_record as _save_chat_record_helper,
    save_packet_record as _save_packet_record_helper,
)
from .history_read_api import (
    load_connections_data as _load_connections_data_helper,
    load_node_capabilities_data as _load_node_capabilities_data_helper,
    load_node_saved_counts_data as _load_node_saved_counts_data_helper,
    load_recent_chat_data as _load_recent_chat_data_helper,
    load_recent_packets_data as _load_recent_packets_data_helper,
)
from .history_read_history import (
    load_node_history_data as _load_node_history_data_helper,
    load_online_activity_data as _load_online_activity_data_helper,
)
from .history_maintenance import (
    next_prune_counter as _next_prune_counter_helper,
    prune_history_tables_now as _prune_history_tables_now_helper,
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
        _prune_history_tables_now_helper(
            self._conn,
            retention_seconds=self.retention_seconds,
            event_retention_seconds=self.event_retention_seconds,
            rollup_retention_seconds=self.rollup_retention_seconds,
            max_rows=self.max_rows,
            event_max_rows=self.event_max_rows,
            prune_history_tables_fn=_prune_history_tables_helper,
            now_unix_fn=time.time,
        )

    def _maybe_prune_unlocked(self) -> None:
        self._writes_since_prune, should_prune = _next_prune_counter_helper(
            self._writes_since_prune
        )
        if not should_prune:
            return
        self._prune_unlocked()

    def load_recent_packets(self, limit: int) -> list[Dict[str, Any]]:
        with self._lock:
            return _load_recent_packets_data_helper(
                self._conn,
                limit=limit,
                fetch_recent_packet_rows_fn=_fetch_recent_packet_rows_helper,
                decode_recent_packets_rows_fn=_decode_recent_packets_rows_helper,
            )

    def load_recent_chat(self, limit: int) -> list[Dict[str, Any]]:
        with self._lock:
            return _load_recent_chat_data_helper(
                self._conn,
                limit=limit,
                fetch_recent_chat_rows_fn=_fetch_recent_chat_rows_helper,
                decode_recent_chat_rows_fn=_decode_recent_chat_rows_helper,
            )

    def load_connections(self) -> list[Dict[str, Any]]:
        with self._lock:
            return _load_connections_data_helper(
                self._conn,
                fetch_connection_rows_fn=_fetch_connection_rows_helper,
                decode_connections_rows_fn=_decode_connections_rows_helper,
            )

    def load_node_history(self, node_id: str, window_hours: int, max_points: int) -> Dict[str, Any]:
        with self._lock:
            return _load_node_history_data_helper(
                self._conn,
                node_id=node_id,
                window_hours=window_hours,
                max_points=max_points,
                fetch_node_history_rows_fn=_fetch_node_history_rows_helper,
                build_node_history_payload_fn=_build_node_history_payload_helper,
                now_unix_fn=time.time,
            )

    def load_online_activity(self, window_hours: int) -> Dict[str, Any]:
        with self._lock:
            return _load_online_activity_data_helper(
                self._conn,
                window_hours=window_hours,
                fetch_online_activity_rows_fn=_fetch_online_activity_rows_helper,
                build_online_activity_payload_fn=_build_online_activity_payload_helper,
                now_unix_fn=time.time,
            )

    def load_node_saved_counts(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return _load_node_saved_counts_data_helper(
                self._conn,
                fetch_node_saved_count_rows_fn=_fetch_node_saved_count_rows_helper,
                decode_node_saved_counts_rows_fn=_decode_node_saved_counts_rows_helper,
            )

    def load_node_capabilities(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return _load_node_capabilities_data_helper(
                self._conn,
                fetch_node_capability_rows_fn=_fetch_node_capability_rows_helper,
                decode_node_capabilities_rows_fn=_decode_node_capabilities_rows_helper,
            )

    def save_connection_event(
        self,
        from_id: str,
        to_id: str,
        rx_time: Optional[int],
        portnum: Optional[str],
        hops: Optional[int],
    ) -> None:
        with self._lock:
            _save_connection_event_helper(
                self._conn,
                from_id=from_id,
                to_id=to_id,
                rx_time=rx_time,
                portnum=portnum,
                hops=hops,
                now_unix_fn=time.time,
            )

            self._maybe_prune_unlocked()
            self._conn.commit()

    def save_packet(self, packet_entry: Dict[str, Any]) -> None:
        with self._lock:
            _save_packet_record_helper(
                self._conn,
                packet_entry,
                now_unix_fn=time.time,
                save_packet_event_and_rollups_fn=_save_packet_event_and_rollups_helper,
            )
            self._maybe_prune_unlocked()
            self._conn.commit()

    def save_chat(self, chat_entry: Dict[str, Any]) -> None:
        with self._lock:
            _save_chat_record_helper(self._conn, chat_entry, now_unix_fn=time.time)
            self._maybe_prune_unlocked()
            self._conn.commit()
