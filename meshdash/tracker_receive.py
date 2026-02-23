from typing import Any, Dict


def process_parsed_tracker_packet(
    *,
    packet: Dict[str, Any],
    parsed: Dict[str, Any],
    include_live_count: bool,
    session_edges: Dict[Any, Dict[str, Any]],
    historical_edges: Dict[Any, Dict[str, Any]],
    port_counts: Any,
    apply_tracker_observation_fn,
    apply_routing_delivery_update_fn,
    extract_update_fn,
    set_delivery_state_fn,
    record_direct_edge_observation_fn,
    build_tracker_packet_artifacts_fn,
    build_packet_summary_fn,
    build_chat_entry_from_packet_fn,
    utc_now_fn,
    format_epoch_fn,
    to_int_fn,
    to_jsonable_fn,
    apply_tracker_storage_updates_fn,
    recent_packets: Any,
    recent_chat: Any,
    history_store: Any,
) -> None:
    rx_time = parsed["rx_time"]
    hops = parsed["hops"]
    portnum = parsed["portnum"]

    direct_key = apply_tracker_observation_fn(
        parsed=parsed,
        include_live_count=include_live_count,
        session_edges=session_edges,
        historical_edges=historical_edges,
        port_counts=port_counts,
        apply_routing_delivery_update_fn=apply_routing_delivery_update_fn,
        extract_update_fn=extract_update_fn,
        set_delivery_state_fn=set_delivery_state_fn,
        record_direct_edge_observation_fn=record_direct_edge_observation_fn,
    )

    packet_entry, chat_entry = build_tracker_packet_artifacts_fn(
        packet=packet,
        parsed=parsed,
        include_live_count=include_live_count,
        build_packet_summary_fn=build_packet_summary_fn,
        build_chat_entry_from_packet_fn=build_chat_entry_from_packet_fn,
        utc_now_fn=utc_now_fn,
        format_epoch_fn=format_epoch_fn,
        to_int_fn=to_int_fn,
        to_jsonable_fn=to_jsonable_fn,
    )
    apply_tracker_storage_updates_fn(
        recent_packets=recent_packets,
        recent_chat=recent_chat,
        history_store=history_store,
        include_live_count=include_live_count,
        direct_key=direct_key,
        rx_time=rx_time,
        portnum=portnum,
        hops=hops,
        packet_entry=packet_entry,
        chat_entry=chat_entry,
    )
