from collections import Counter, deque

from meshdash.tracker_runtime_packet_contracts import TrackerPacketRuntimeDependencies
from meshdash.tracker_runtime_receive_dependencies import (
    build_tracker_packet_runtime_dependencies,
    tracker_packet_runtime_dependencies_to_legacy_kwargs,
)


def test_build_tracker_packet_runtime_dependencies_binds_tracker_and_overrides():
    tracker = type(
        "_Tracker",
        (),
        {
            "edges": {"edge": 1},
            "_historical_edges": {"historical": 2},
            "port_counts": Counter(),
            "recent_packets": deque(maxlen=4),
            "recent_chat": deque(maxlen=4),
            "_history_store": "history-store",
            "_extract_delivery_update_fn": "extract-delivery",
            "_set_delivery_state_fn": "set-delivery",
        },
    )()

    sentinel = {
        "get_node_id_from_num_fn": object(),
        "apply_tracker_observation_fn": object(),
        "apply_routing_delivery_update_fn": object(),
        "record_direct_edge_observation_fn": object(),
        "build_tracker_packet_artifacts_fn": object(),
        "build_packet_summary_fn": object(),
        "build_chat_entry_from_packet_fn": object(),
        "apply_tracker_storage_updates_fn": object(),
        "parse_tracker_packet_fn": object(),
        "process_parsed_tracker_packet_fn": object(),
        "to_int_fn": object(),
        "calculate_hops_fn": object(),
        "extract_packet_position_fn": object(),
        "extract_packet_battery_level_fn": object(),
        "extract_reply_id_fn": object(),
        "extract_emoji_codepoint_fn": object(),
        "emoji_from_codepoint_fn": object(),
        "utc_now_fn": object(),
        "format_epoch_fn": object(),
        "to_jsonable_fn": object(),
    }

    deps = build_tracker_packet_runtime_dependencies(
        tracker,
        get_node_id_from_num_fn=sentinel["get_node_id_from_num_fn"],
        apply_tracker_observation_fn=sentinel["apply_tracker_observation_fn"],
        apply_routing_delivery_update_fn=sentinel["apply_routing_delivery_update_fn"],
        record_direct_edge_observation_fn=sentinel["record_direct_edge_observation_fn"],
        build_tracker_packet_artifacts_fn=sentinel["build_tracker_packet_artifacts_fn"],
        build_packet_summary_fn=sentinel["build_packet_summary_fn"],
        build_chat_entry_from_packet_fn=sentinel["build_chat_entry_from_packet_fn"],
        apply_tracker_storage_updates_fn=sentinel["apply_tracker_storage_updates_fn"],
        parse_tracker_packet_fn=sentinel["parse_tracker_packet_fn"],
        process_parsed_tracker_packet_fn=sentinel["process_parsed_tracker_packet_fn"],
        to_int_fn=sentinel["to_int_fn"],
        calculate_hops_fn=sentinel["calculate_hops_fn"],
        extract_packet_position_fn=sentinel["extract_packet_position_fn"],
        extract_packet_battery_level_fn=sentinel["extract_packet_battery_level_fn"],
        extract_reply_id_fn=sentinel["extract_reply_id_fn"],
        extract_emoji_codepoint_fn=sentinel["extract_emoji_codepoint_fn"],
        emoji_from_codepoint_fn=sentinel["emoji_from_codepoint_fn"],
        utc_now_fn=sentinel["utc_now_fn"],
        format_epoch_fn=sentinel["format_epoch_fn"],
        to_jsonable_fn=sentinel["to_jsonable_fn"],
    )

    assert isinstance(deps, TrackerPacketRuntimeDependencies)
    assert deps.session_edges is tracker.edges
    assert deps.historical_edges is tracker._historical_edges
    assert deps.port_counts is tracker.port_counts
    assert deps.recent_packets is tracker.recent_packets
    assert deps.recent_chat is tracker.recent_chat
    assert deps.history_store == "history-store"
    assert deps.extract_delivery_update_fn == "extract-delivery"
    assert deps.set_delivery_state_fn == "set-delivery"

    for key, value in sentinel.items():
        assert getattr(deps, key) is value


def test_tracker_packet_runtime_dependencies_to_legacy_kwargs_maps_fields():
    deps = TrackerPacketRuntimeDependencies(
        session_edges={"edge": 1},
        historical_edges={"historical": 2},
        port_counts=object(),
        recent_packets=object(),
        recent_chat=object(),
        history_store=object(),
        extract_delivery_update_fn=object(),
        set_delivery_state_fn=object(),
        apply_tracker_observation_fn=object(),
        apply_routing_delivery_update_fn=object(),
        record_direct_edge_observation_fn=object(),
        build_tracker_packet_artifacts_fn=object(),
        build_packet_summary_fn=object(),
        build_chat_entry_from_packet_fn=object(),
        apply_tracker_storage_updates_fn=object(),
        parse_tracker_packet_fn=object(),
        process_parsed_tracker_packet_fn=object(),
        get_node_id_from_num_fn=object(),
        to_int_fn=object(),
        calculate_hops_fn=object(),
        extract_packet_position_fn=object(),
        extract_packet_battery_level_fn=object(),
        extract_reply_id_fn=object(),
        extract_emoji_codepoint_fn=object(),
        emoji_from_codepoint_fn=object(),
        utc_now_fn=object(),
        format_epoch_fn=object(),
        to_jsonable_fn=object(),
    )

    payload = tracker_packet_runtime_dependencies_to_legacy_kwargs(deps)

    assert isinstance(payload, dict)
    assert payload["session_edges"] is deps.session_edges
    assert payload["historical_edges"] is deps.historical_edges
    assert payload["port_counts"] is deps.port_counts
    assert payload["recent_packets"] is deps.recent_packets
    assert payload["recent_chat"] is deps.recent_chat
    assert payload["history_store"] is deps.history_store
    assert payload["extract_delivery_update_fn"] is deps.extract_delivery_update_fn
    assert payload["set_delivery_state_fn"] is deps.set_delivery_state_fn
    assert payload["apply_tracker_observation_fn"] is deps.apply_tracker_observation_fn
    assert payload["apply_routing_delivery_update_fn"] is deps.apply_routing_delivery_update_fn
    assert payload["record_direct_edge_observation_fn"] is deps.record_direct_edge_observation_fn
    assert payload["build_tracker_packet_artifacts_fn"] is deps.build_tracker_packet_artifacts_fn
    assert payload["build_packet_summary_fn"] is deps.build_packet_summary_fn
    assert payload["build_chat_entry_from_packet_fn"] is deps.build_chat_entry_from_packet_fn
    assert payload["apply_tracker_storage_updates_fn"] is deps.apply_tracker_storage_updates_fn
    assert payload["parse_tracker_packet_fn"] is deps.parse_tracker_packet_fn
    assert payload["process_parsed_tracker_packet_fn"] is deps.process_parsed_tracker_packet_fn
    assert payload["get_node_id_from_num_fn"] is deps.get_node_id_from_num_fn
    assert payload["to_int_fn"] is deps.to_int_fn
    assert payload["calculate_hops_fn"] is deps.calculate_hops_fn
    assert payload["extract_packet_position_fn"] is deps.extract_packet_position_fn
    assert payload["extract_packet_battery_level_fn"] is deps.extract_packet_battery_level_fn
    assert payload["extract_reply_id_fn"] is deps.extract_reply_id_fn
    assert payload["extract_emoji_codepoint_fn"] is deps.extract_emoji_codepoint_fn
    assert payload["emoji_from_codepoint_fn"] is deps.emoji_from_codepoint_fn
    assert payload["utc_now_fn"] is deps.utc_now_fn
    assert payload["format_epoch_fn"] is deps.format_epoch_fn
    assert payload["to_jsonable_fn"] is deps.to_jsonable_fn
