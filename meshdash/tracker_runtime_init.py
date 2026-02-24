from typing import Any

from .tracker_callbacks import TrackerDeliveryCallbacks


def initialize_dashboard_tracker_runtime(
    tracker: Any,
    *,
    packet_limit: int,
    history_store: Any,
    default_chat_delivery_timeout_seconds: int,
    initialize_tracker_buffers_fn: Any,
    build_tracker_delivery_callbacks_fn: Any,
    apply_tracker_history_bootstrap_fn: Any,
    load_tracker_history_bootstrap_fn: Any,
    build_historical_edges_fn: Any,
    parse_utc_text_to_unix_fn: Any,
    utc_now_fn: Any,
    to_int_fn: Any,
    now_unix_fn: Any,
) -> None:
    tracker._history_store = history_store
    tracker._chat_delivery_timeout_seconds = int(default_chat_delivery_timeout_seconds)
    tracker.live_packet_count = 0

    buffers = initialize_tracker_buffers_fn(packet_limit)
    tracker.edges = buffers.edges
    tracker._historical_edges = buffers.historical_edges
    tracker.port_counts = buffers.port_counts
    tracker.recent_packets = buffers.recent_packets
    tracker.recent_chat = buffers.recent_chat

    delivery_callbacks: TrackerDeliveryCallbacks = build_tracker_delivery_callbacks_fn(
        tracker.recent_chat,
        get_timeout_seconds_fn=lambda: tracker._chat_delivery_timeout_seconds,
        to_int_fn=to_int_fn,
        parse_utc_text_to_unix_fn=parse_utc_text_to_unix_fn,
        utc_now_fn=utc_now_fn,
        now_unix_fn=now_unix_fn,
    )
    tracker._set_delivery_state_fn = delivery_callbacks.set_delivery_state
    tracker._extract_delivery_update_fn = delivery_callbacks.extract_delivery_update
    tracker._expire_pending_deliveries_fn = delivery_callbacks.expire_pending_deliveries

    tracker._historical_edges = apply_tracker_history_bootstrap_fn(
        history_store=tracker._history_store,
        packet_limit=packet_limit,
        recent_packets=tracker.recent_packets,
        recent_chat=tracker.recent_chat,
        load_tracker_history_bootstrap_fn=load_tracker_history_bootstrap_fn,
        build_historical_edges_fn=build_historical_edges_fn,
    )
