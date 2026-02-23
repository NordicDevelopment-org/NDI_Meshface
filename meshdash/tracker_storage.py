from collections import deque
from typing import Any, Dict, Optional, Tuple


def apply_tracker_storage_updates(
    *,
    recent_packets: deque[Dict[str, Any]],
    recent_chat: deque[Dict[str, Any]],
    history_store: Any,
    include_live_count: bool,
    direct_key: Optional[Tuple[str, str]],
    rx_time: Optional[int],
    portnum: Optional[Any],
    hops: Optional[int],
    packet_entry: Dict[str, Any],
    chat_entry: Optional[Dict[str, Any]],
) -> None:
    if direct_key is not None and include_live_count and history_store is not None:
        history_store.save_connection_event(
            from_id=direct_key[0],
            to_id=direct_key[1],
            rx_time=rx_time,
            portnum=str(portnum) if portnum is not None else None,
            hops=hops,
        )

    recent_packets.append(packet_entry)
    if history_store is not None and include_live_count:
        history_store.save_packet(packet_entry)

    if chat_entry is not None:
        recent_chat.append(chat_entry)
        if history_store is not None and include_live_count:
            history_store.save_chat(chat_entry)
