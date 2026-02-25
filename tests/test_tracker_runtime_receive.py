from collections import Counter, deque

from meshdash.tracker_runtime_packet_contracts import TrackerPacketRuntimeDependencies
from meshdash.tracker_runtime_receive import record_tracker_receive_unlocked


def test_record_tracker_receive_unlocked_forwards_tracker_context_and_expires():
    observed = {}

    def _record_tracker_packet_unlocked(**kwargs):
        observed["record_kwargs"] = kwargs

    def _expire(self):
        observed["expired"] = True

    tracker = type(
        "_Tracker",
        (),
        {
            "edges": {"edge": 1},
            "_historical_edges": {"historical": 2},
            "port_counts": Counter(),
            "recent_packets": deque(maxlen=8),
            "recent_chat": deque(maxlen=8),
            "_history_store": "history-store",
            "_extract_delivery_update_fn": "extract-delivery",
            "_set_delivery_state_fn": "set-delivery",
            "_expire_pending_deliveries_fn": _expire,
        },
    )()

    packet = {"id": 1}
    interface = object()
    sentinel_get_node_id = object()
    sentinel_observe = object()
    sentinel_apply_delivery = object()
    sentinel_record_edge = object()
    sentinel_build_artifacts = object()
    sentinel_build_summary = object()
    sentinel_build_chat = object()
    sentinel_apply_storage = object()
    sentinel_parse = object()
    sentinel_process = object()
    sentinel_to_int = object()
    sentinel_hops = object()
    sentinel_pos = object()
    sentinel_battery = object()
    sentinel_reply = object()
    sentinel_codepoint = object()
    sentinel_emoji = object()
    sentinel_utc_now = object()
    sentinel_format_epoch = object()
    sentinel_to_jsonable = object()

    record_tracker_receive_unlocked(
        tracker,
        packet=packet,
        interface=interface,
        include_live_count=True,
        get_node_id_from_num_fn=sentinel_get_node_id,
        record_tracker_packet_unlocked_fn=_record_tracker_packet_unlocked,
        apply_tracker_observation_fn=sentinel_observe,
        apply_routing_delivery_update_fn=sentinel_apply_delivery,
        record_direct_edge_observation_fn=sentinel_record_edge,
        build_tracker_packet_artifacts_fn=sentinel_build_artifacts,
        build_packet_summary_fn=sentinel_build_summary,
        build_chat_entry_from_packet_fn=sentinel_build_chat,
        apply_tracker_storage_updates_fn=sentinel_apply_storage,
        parse_tracker_packet_fn=sentinel_parse,
        process_parsed_tracker_packet_fn=sentinel_process,
        to_int_fn=sentinel_to_int,
        calculate_hops_fn=sentinel_hops,
        extract_packet_position_fn=sentinel_pos,
        extract_packet_battery_level_fn=sentinel_battery,
        extract_reply_id_fn=sentinel_reply,
        extract_emoji_codepoint_fn=sentinel_codepoint,
        emoji_from_codepoint_fn=sentinel_emoji,
        utc_now_fn=sentinel_utc_now,
        format_epoch_fn=sentinel_format_epoch,
        to_jsonable_fn=sentinel_to_jsonable,
    )

    assert observed["record_kwargs"] == {
        "packet": packet,
        "interface": interface,
        "include_live_count": True,
        "session_edges": tracker.edges,
        "historical_edges": tracker._historical_edges,
        "port_counts": tracker.port_counts,
        "recent_packets": tracker.recent_packets,
        "recent_chat": tracker.recent_chat,
        "history_store": "history-store",
        "extract_delivery_update_fn": "extract-delivery",
        "set_delivery_state_fn": "set-delivery",
        "apply_tracker_observation_fn": sentinel_observe,
        "apply_routing_delivery_update_fn": sentinel_apply_delivery,
        "record_direct_edge_observation_fn": sentinel_record_edge,
        "build_tracker_packet_artifacts_fn": sentinel_build_artifacts,
        "build_packet_summary_fn": sentinel_build_summary,
        "build_chat_entry_from_packet_fn": sentinel_build_chat,
        "apply_tracker_storage_updates_fn": sentinel_apply_storage,
        "parse_tracker_packet_fn": sentinel_parse,
        "process_parsed_tracker_packet_fn": sentinel_process,
        "get_node_id_from_num_fn": sentinel_get_node_id,
        "to_int_fn": sentinel_to_int,
        "calculate_hops_fn": sentinel_hops,
        "extract_packet_position_fn": sentinel_pos,
        "extract_packet_battery_level_fn": sentinel_battery,
        "extract_reply_id_fn": sentinel_reply,
        "extract_emoji_codepoint_fn": sentinel_codepoint,
        "emoji_from_codepoint_fn": sentinel_emoji,
        "utc_now_fn": sentinel_utc_now,
        "format_epoch_fn": sentinel_format_epoch,
        "to_jsonable_fn": sentinel_to_jsonable,
    }
    assert observed["expired"] is True


def test_record_tracker_receive_unlocked_uses_typed_path_by_default():
    observed = {}

    def _record_tracker_packet_unlocked_with_dependencies(**kwargs):
        observed["record_kwargs"] = kwargs

    def _expire(self):
        observed["expired"] = True

    tracker = type(
        "_Tracker",
        (),
        {
            "edges": {"edge": 1},
            "_historical_edges": {"historical": 2},
            "port_counts": Counter(),
            "recent_packets": deque(maxlen=8),
            "recent_chat": deque(maxlen=8),
            "_history_store": "history-store",
            "_extract_delivery_update_fn": "extract-delivery",
            "_set_delivery_state_fn": "set-delivery",
            "_expire_pending_deliveries_fn": _expire,
        },
    )()

    packet = {"id": 99}
    interface = object()
    sentinel_get_node_id = object()

    record_tracker_receive_unlocked(
        tracker,
        packet=packet,
        interface=interface,
        include_live_count=False,
        get_node_id_from_num_fn=sentinel_get_node_id,
        record_tracker_packet_unlocked_with_dependencies_fn=_record_tracker_packet_unlocked_with_dependencies,
    )

    record_kwargs = observed["record_kwargs"]
    assert record_kwargs["packet"] is packet
    assert record_kwargs["interface"] is interface
    assert record_kwargs["include_live_count"] is False
    deps = record_kwargs["deps"]
    assert isinstance(deps, TrackerPacketRuntimeDependencies)
    assert deps.get_node_id_from_num_fn is sentinel_get_node_id
    assert deps.session_edges is tracker.edges
    assert deps.historical_edges is tracker._historical_edges
    assert deps.port_counts is tracker.port_counts
    assert deps.recent_packets is tracker.recent_packets
    assert deps.recent_chat is tracker.recent_chat
    assert deps.history_store == "history-store"
    assert observed["expired"] is True
