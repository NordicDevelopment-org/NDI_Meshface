from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TrackerPacketRuntimeDependencies:
    session_edges: Any
    historical_edges: Any
    port_counts: Any
    recent_packets: Any
    recent_chat: Any
    history_store: Any
    extract_delivery_update_fn: Any
    set_delivery_state_fn: Any
    apply_tracker_observation_fn: Any
    apply_routing_delivery_update_fn: Any
    record_direct_edge_observation_fn: Any
    build_tracker_packet_artifacts_fn: Any
    build_packet_summary_fn: Any
    build_chat_entry_from_packet_fn: Any
    apply_tracker_storage_updates_fn: Any
    parse_tracker_packet_fn: Any
    process_parsed_tracker_packet_fn: Any
    get_node_id_from_num_fn: Any
    to_int_fn: Any
    calculate_hops_fn: Any
    extract_packet_position_fn: Any
    extract_packet_battery_level_fn: Any
    extract_reply_id_fn: Any
    extract_emoji_codepoint_fn: Any
    emoji_from_codepoint_fn: Any
    utc_now_fn: Any
    format_epoch_fn: Any
    to_jsonable_fn: Any
