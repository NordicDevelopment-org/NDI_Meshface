import threading
import time
from collections import Counter, deque
from typing import Any, Dict, Optional, Tuple

try:
    import meshtastic
except Exception:
    meshtastic = None

from .chat import (
    build_local_chat_entry as _build_local_chat_entry,
    chat_message_id as _chat_message_id_helper,
    expire_pending_deliveries as _expire_pending_deliveries_helper,
    extract_routing_delivery_update as _extract_routing_delivery_update_helper,
    set_delivery_state as _set_delivery_state_helper,
)
from .helpers import (
    calculate_hops as _calculate_hops,
    emoji_from_codepoint as _emoji_from_codepoint,
    extract_emoji_codepoint as _extract_emoji_codepoint,
    extract_packet_battery_level as _extract_packet_battery_level,
    extract_packet_position as _extract_packet_position,
    extract_reply_id as _extract_reply_id,
    format_epoch as _format_epoch,
    safe_json_loads as _safe_json_loads,
    to_int as _to_int,
    to_jsonable as _to_jsonable,
)
from .history_store import HistoryStore
from .nodes import (
    get_node_id_from_num as _get_node_id_from_num_helper,
    parse_utc_text_to_unix as _parse_utc_text_to_unix,
    utc_now as _utc_now,
)
from .tracker_snapshot import (
    build_edge_snapshot_rows as _build_edge_snapshot_rows_helper,
    build_tracker_snapshot_payload as _build_tracker_snapshot_payload_helper,
)
from .tracker_edges import (
    record_direct_edge_observation as _record_direct_edge_observation_helper,
)
from .tracker_history_edges import (
    build_historical_edges as _build_historical_edges_helper,
)
from .tracker_bootstrap import (
    load_tracker_history_bootstrap as _load_tracker_history_bootstrap_helper,
)
from .tracker_entries import (
    build_chat_entry_from_packet as _build_chat_entry_from_packet_helper,
    build_packet_summary as _build_packet_summary_helper,
)
from .tracker_ingest import (
    parse_tracker_packet as _parse_tracker_packet_helper,
)
from .tracker_storage import (
    apply_tracker_storage_updates as _apply_tracker_storage_updates_helper,
)
from .tracker_delivery import (
    apply_routing_delivery_update as _apply_routing_delivery_update_helper,
)
from .tracker_local_chat import (
    append_local_chat_entry as _append_local_chat_entry_helper,
)
from .tracker_seed import (
    seed_tracker_from_node_db as _seed_tracker_from_node_db_helper,
)
from .tracker_packet_artifacts import (
    build_tracker_packet_artifacts as _build_tracker_packet_artifacts_helper,
)
from .tracker_observation import (
    apply_tracker_observation as _apply_tracker_observation_helper,
)


DEFAULT_CHAT_DELIVERY_TIMEOUT_SECONDS = 90
MIN_REAL_LINK_COUNT = 2


def _get_node_id_from_num(iface: Any, node_num: Any) -> Optional[str]:
    broadcast_num = getattr(meshtastic, "BROADCAST_NUM", None) if meshtastic is not None else None
    return _get_node_id_from_num_helper(
        iface,
        node_num,
        broadcast_num=broadcast_num,
        to_int_fn=_to_int,
    )


class DashboardTracker:
    def __init__(self, packet_limit: int, history_store: Optional[HistoryStore] = None) -> None:
        self._lock = threading.Lock()
        self._history_store = history_store
        self._chat_delivery_timeout_seconds = DEFAULT_CHAT_DELIVERY_TIMEOUT_SECONDS
        self.live_packet_count = 0
        self.edges: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self._historical_edges: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.port_counts: Counter[str] = Counter()
        self.recent_packets: deque[Dict[str, Any]] = deque(maxlen=packet_limit)
        self.recent_chat: deque[Dict[str, Any]] = deque(maxlen=packet_limit)

        if self._history_store is not None:
            bootstrap = _load_tracker_history_bootstrap_helper(
                self._history_store,
                packet_limit=packet_limit,
                build_historical_edges_fn=_build_historical_edges_helper,
            )
            self.recent_packets.extend(bootstrap["recent_packets"])
            self.recent_chat.extend(bootstrap["recent_chat"])
            self._historical_edges = bootstrap["historical_edges"]

    def on_receive(self, packet: Dict[str, Any], interface: Any) -> None:
        with self._lock:
            self.live_packet_count += 1
            self._record_packet_unlocked(packet, interface, include_live_count=True)

    def has_recent_packets(self) -> bool:
        with self._lock:
            return bool(self.recent_packets)

    def load_node_saved_counts(self) -> Dict[str, Dict[str, Any]]:
        if self._history_store is None:
            return {}
        return self._history_store.load_node_saved_counts()

    def load_node_capabilities(self) -> Dict[str, Dict[str, Any]]:
        if self._history_store is None:
            return {}
        return self._history_store.load_node_capabilities()

    def _chat_message_id(self, entry: Any) -> Optional[int]:
        return _chat_message_id_helper(entry, to_int_fn=_to_int)

    def _set_delivery_state_unlocked(
        self,
        message_id: Any,
        state: str,
        error: Optional[str] = None,
    ) -> bool:
        return _set_delivery_state_helper(
            self.recent_chat,
            message_id=message_id,
            state=state,
            error=error,
            to_int_fn=_to_int,
            now_text_fn=_utc_now,
            now_unix_fn=lambda: int(time.time()),
        )

    def _extract_routing_delivery_update_unlocked(self, decoded: Any) -> Optional[Dict[str, Any]]:
        return _extract_routing_delivery_update_helper(decoded, to_int_fn=_to_int)

    def _expire_pending_deliveries_unlocked(self) -> None:
        _expire_pending_deliveries_helper(
            self.recent_chat,
            timeout_seconds=self._chat_delivery_timeout_seconds,
            to_int_fn=_to_int,
            parse_utc_text_to_unix_fn=_parse_utc_text_to_unix,
            now_unix_fn=lambda: int(time.time()),
            now_text_fn=_utc_now,
        )

    def record_local_chat(
        self,
        text: str,
        from_id: str = "local",
        to_id: str = "^all",
        channel_index: int = 0,
        message_id: Optional[int] = None,
        reply_id: Optional[int] = None,
        emoji: Optional[str] = None,
        emoji_codepoint: Optional[int] = None,
        is_reaction: bool = False,
        ack_requested: bool = False,
        retry_of: Optional[int] = None,
    ) -> None:
        now_text = _utc_now()
        now_unix = int(time.time())
        entry = _build_local_chat_entry(
            text=text,
            from_id=from_id,
            to_id=to_id,
            channel_index=channel_index,
            message_id=message_id,
            reply_id=reply_id,
            emoji=emoji,
            emoji_codepoint=emoji_codepoint,
            is_reaction=is_reaction,
            ack_requested=ack_requested,
            retry_of=retry_of,
            now_text=now_text,
            now_unix=now_unix,
            to_int_fn=_to_int,
            emoji_from_codepoint_fn=_emoji_from_codepoint,
        )
        if entry is None:
            return
        with self._lock:
            _append_local_chat_entry_helper(
                recent_chat=self.recent_chat,
                history_store=self._history_store,
                entry=entry,
            )

    def seed_packet(self, packet: Dict[str, Any], interface: Any) -> None:
        with self._lock:
            self._record_packet_unlocked(packet, interface, include_live_count=False)

    def _record_packet_unlocked(
        self, packet: Dict[str, Any], interface: Any, include_live_count: bool
    ) -> None:
        parsed = _parse_tracker_packet_helper(
            packet,
            interface,
            get_node_id_from_num_fn=_get_node_id_from_num,
            to_int_fn=_to_int,
            calculate_hops_fn=_calculate_hops,
            extract_packet_position_fn=_extract_packet_position,
            extract_packet_battery_level_fn=_extract_packet_battery_level,
            extract_reply_id_fn=_extract_reply_id,
            extract_emoji_codepoint_fn=_extract_emoji_codepoint,
            emoji_from_codepoint_fn=_emoji_from_codepoint,
        )
        rx_time = parsed["rx_time"]
        hops = parsed["hops"]
        portnum = parsed["portnum"]
        direct_key = _apply_tracker_observation_helper(
            parsed=parsed,
            include_live_count=include_live_count,
            session_edges=self.edges,
            historical_edges=self._historical_edges,
            port_counts=self.port_counts,
            apply_routing_delivery_update_fn=_apply_routing_delivery_update_helper,
            extract_update_fn=self._extract_routing_delivery_update_unlocked,
            set_delivery_state_fn=self._set_delivery_state_unlocked,
            record_direct_edge_observation_fn=_record_direct_edge_observation_helper,
        )

        packet_entry, chat_entry = _build_tracker_packet_artifacts_helper(
            packet=packet,
            parsed=parsed,
            include_live_count=include_live_count,
            build_packet_summary_fn=_build_packet_summary_helper,
            build_chat_entry_from_packet_fn=_build_chat_entry_from_packet_helper,
            utc_now_fn=_utc_now,
            format_epoch_fn=_format_epoch,
            to_int_fn=_to_int,
            to_jsonable_fn=_to_jsonable,
        )
        _apply_tracker_storage_updates_helper(
            recent_packets=self.recent_packets,
            recent_chat=self.recent_chat,
            history_store=self._history_store,
            include_live_count=include_live_count,
            direct_key=direct_key,
            rx_time=rx_time,
            portnum=portnum,
            hops=hops,
            packet_entry=packet_entry,
            chat_entry=chat_entry,
        )

        self._expire_pending_deliveries_unlocked()

    def snapshot(self, nodes_by_id: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        with self._lock:
            self._expire_pending_deliveries_unlocked()
            return _build_tracker_snapshot_payload_helper(
                session_edges=self.edges,
                historical_edges=self._historical_edges,
                nodes_by_id=nodes_by_id,
                port_counts=self.port_counts,
                recent_packets=self.recent_packets,
                recent_chat=self.recent_chat,
                live_packet_count=self.live_packet_count,
                min_real_link_count=MIN_REAL_LINK_COUNT,
                format_epoch_fn=_format_epoch,
                build_edge_snapshot_rows_fn=_build_edge_snapshot_rows_helper,
            )


def seed_tracker_from_node_db(tracker: DashboardTracker, iface: Any) -> None:
    _seed_tracker_from_node_db_helper(tracker, iface)
