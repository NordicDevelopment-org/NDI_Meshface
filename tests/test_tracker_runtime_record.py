from collections import Counter, deque

from meshdash.tracker_runtime_record import record_tracker_packet_unlocked


def test_record_tracker_packet_unlocked_parses_then_processes():
    observed = {}
    parsed = {"rx_time": 100, "hops": 3, "portnum": "TEXT_MESSAGE_APP"}
    packet = {"id": 1}
    interface = object()
    session_edges = {}
    historical_edges = {}
    port_counts = Counter()
    recent_packets = deque(maxlen=4)
    recent_chat = deque(maxlen=4)

    def _parse(pkt, iface, **kwargs):
        observed["parse_packet"] = pkt
        observed["parse_interface"] = iface
        observed["parse_kwargs"] = kwargs
        return parsed

    def _process(**kwargs):
        observed["process_kwargs"] = kwargs

    sentinel_observe = object()
    sentinel_apply_delivery = object()
    sentinel_extract = object()
    sentinel_set_state = object()
    sentinel_record_edge = object()
    sentinel_build_artifacts = object()
    sentinel_build_summary = object()
    sentinel_build_chat = object()
    sentinel_apply_storage = object()
    sentinel_get_node_id = object()
    sentinel_to_int = object()
    sentinel_hops = object()
    sentinel_pos = object()
    sentinel_battery = object()
    sentinel_reply = object()
    sentinel_codepoint = object()
    sentinel_emoji = object()
    sentinel_utc_now = object()
    sentinel_format = object()
    sentinel_to_json = object()

    record_tracker_packet_unlocked(
        packet=packet,
        interface=interface,
        include_live_count=True,
        session_edges=session_edges,
        historical_edges=historical_edges,
        port_counts=port_counts,
        recent_packets=recent_packets,
        recent_chat=recent_chat,
        history_store="history-store",
        extract_delivery_update_fn=sentinel_extract,
        set_delivery_state_fn=sentinel_set_state,
        apply_tracker_observation_fn=sentinel_observe,
        apply_routing_delivery_update_fn=sentinel_apply_delivery,
        record_direct_edge_observation_fn=sentinel_record_edge,
        build_tracker_packet_artifacts_fn=sentinel_build_artifacts,
        build_packet_summary_fn=sentinel_build_summary,
        build_chat_entry_from_packet_fn=sentinel_build_chat,
        apply_tracker_storage_updates_fn=sentinel_apply_storage,
        parse_tracker_packet_fn=_parse,
        process_parsed_tracker_packet_fn=_process,
        get_node_id_from_num_fn=sentinel_get_node_id,
        to_int_fn=sentinel_to_int,
        calculate_hops_fn=sentinel_hops,
        extract_packet_position_fn=sentinel_pos,
        extract_packet_battery_level_fn=sentinel_battery,
        extract_reply_id_fn=sentinel_reply,
        extract_emoji_codepoint_fn=sentinel_codepoint,
        emoji_from_codepoint_fn=sentinel_emoji,
        utc_now_fn=sentinel_utc_now,
        format_epoch_fn=sentinel_format,
        to_jsonable_fn=sentinel_to_json,
    )

    assert observed["parse_packet"] is packet
    assert observed["parse_interface"] is interface
    assert observed["parse_kwargs"] == {
        "get_node_id_from_num_fn": sentinel_get_node_id,
        "to_int_fn": sentinel_to_int,
        "calculate_hops_fn": sentinel_hops,
        "extract_packet_position_fn": sentinel_pos,
        "extract_packet_battery_level_fn": sentinel_battery,
        "extract_reply_id_fn": sentinel_reply,
        "extract_emoji_codepoint_fn": sentinel_codepoint,
        "emoji_from_codepoint_fn": sentinel_emoji,
    }

    assert observed["process_kwargs"] == {
        "packet": packet,
        "parsed": parsed,
        "include_live_count": True,
        "session_edges": session_edges,
        "historical_edges": historical_edges,
        "port_counts": port_counts,
        "apply_tracker_observation_fn": sentinel_observe,
        "apply_routing_delivery_update_fn": sentinel_apply_delivery,
        "extract_update_fn": sentinel_extract,
        "set_delivery_state_fn": sentinel_set_state,
        "record_direct_edge_observation_fn": sentinel_record_edge,
        "build_tracker_packet_artifacts_fn": sentinel_build_artifacts,
        "build_packet_summary_fn": sentinel_build_summary,
        "build_chat_entry_from_packet_fn": sentinel_build_chat,
        "utc_now_fn": sentinel_utc_now,
        "format_epoch_fn": sentinel_format,
        "to_int_fn": sentinel_to_int,
        "to_jsonable_fn": sentinel_to_json,
        "apply_tracker_storage_updates_fn": sentinel_apply_storage,
        "recent_packets": recent_packets,
        "recent_chat": recent_chat,
        "history_store": "history-store",
    }
