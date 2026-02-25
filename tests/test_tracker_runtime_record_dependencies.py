from meshdash.tracker_runtime_packet_contracts import TrackerPacketRuntimeDependencies
from meshdash.tracker_runtime_record_dependencies import (
    build_tracker_packet_runtime_dependencies_from_legacy_args,
)


def test_build_tracker_packet_runtime_dependencies_from_legacy_args_maps_all_fields():
    sentinel = {
        "session_edges": {"edge": 1},
        "historical_edges": {"historical": 2},
        "port_counts": object(),
        "recent_packets": object(),
        "recent_chat": object(),
        "history_store": object(),
        "extract_delivery_update_fn": object(),
        "set_delivery_state_fn": object(),
        "apply_tracker_observation_fn": object(),
        "apply_routing_delivery_update_fn": object(),
        "record_direct_edge_observation_fn": object(),
        "build_tracker_packet_artifacts_fn": object(),
        "build_packet_summary_fn": object(),
        "build_chat_entry_from_packet_fn": object(),
        "apply_tracker_storage_updates_fn": object(),
        "parse_tracker_packet_fn": object(),
        "process_parsed_tracker_packet_fn": object(),
        "get_node_id_from_num_fn": object(),
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

    deps = build_tracker_packet_runtime_dependencies_from_legacy_args(**sentinel)

    assert isinstance(deps, TrackerPacketRuntimeDependencies)
    for key, value in sentinel.items():
        assert getattr(deps, key) is value
