from typing import Any, Dict

try:
    import meshtastic
except Exception:
    meshtastic = None

from .helpers import (
    calculate_hops as _calculate_hops,
    emoji_from_codepoint as _emoji_from_codepoint,
    extract_emoji_codepoint as _extract_emoji_codepoint,
    extract_packet_battery_level as _extract_packet_battery_level,
    extract_packet_position as _extract_packet_position,
    extract_reply_id as _extract_reply_id,
    format_epoch as _format_epoch,
    to_int as _to_int,
    to_jsonable as _to_jsonable,
)
from .nodes import (
    utc_now as _utc_now,
)
from .tracker_delivery import (
    apply_routing_delivery_update as _apply_routing_delivery_update_helper,
)
from .tracker_edges import (
    record_direct_edge_observation as _record_direct_edge_observation_helper,
)
from .tracker_entries import (
    build_chat_entry_from_packet as _build_chat_entry_from_packet_helper,
    build_packet_summary as _build_packet_summary_helper,
)
from .tracker_ingest import (
    parse_tracker_packet as _parse_tracker_packet_helper,
)
from .tracker_observation import (
    apply_tracker_observation as _apply_tracker_observation_helper,
)
from .tracker_node_resolver import (
    get_tracker_node_id_from_num as _get_tracker_node_id_from_num_helper,
)
from .tracker_packet_artifacts import (
    build_tracker_packet_artifacts as _build_tracker_packet_artifacts_helper,
)
from .tracker_receive import (
    process_parsed_tracker_packet as _process_parsed_tracker_packet_helper,
)
from .tracker_runtime_record import (
    record_tracker_packet_unlocked as _record_tracker_packet_unlocked_helper,
)
from .tracker_storage import (
    apply_tracker_storage_updates as _apply_tracker_storage_updates_helper,
)


def _resolve_tracker_node_id_from_num(
    iface: Any,
    node_num: Any,
    *,
    meshtastic_module: Any = meshtastic,
    to_int_fn: Any = _to_int,
    get_node_id_from_num_fn: Any,
) -> Any:
    return _get_tracker_node_id_from_num_helper(
        iface,
        node_num,
        meshtastic_module=meshtastic_module,
        to_int_fn=to_int_fn,
        get_node_id_from_num_fn=get_node_id_from_num_fn,
    )


def record_tracker_receive_unlocked(
    tracker: Any,
    *,
    packet: Dict[str, Any],
    interface: Any,
    include_live_count: bool,
    get_node_id_from_num_fn: Any,
    record_tracker_packet_unlocked_fn: Any = _record_tracker_packet_unlocked_helper,
    apply_tracker_observation_fn: Any = _apply_tracker_observation_helper,
    apply_routing_delivery_update_fn: Any = _apply_routing_delivery_update_helper,
    record_direct_edge_observation_fn: Any = _record_direct_edge_observation_helper,
    build_tracker_packet_artifacts_fn: Any = _build_tracker_packet_artifacts_helper,
    build_packet_summary_fn: Any = _build_packet_summary_helper,
    build_chat_entry_from_packet_fn: Any = _build_chat_entry_from_packet_helper,
    apply_tracker_storage_updates_fn: Any = _apply_tracker_storage_updates_helper,
    parse_tracker_packet_fn: Any = _parse_tracker_packet_helper,
    process_parsed_tracker_packet_fn: Any = _process_parsed_tracker_packet_helper,
    to_int_fn: Any = _to_int,
    calculate_hops_fn: Any = _calculate_hops,
    extract_packet_position_fn: Any = _extract_packet_position,
    extract_packet_battery_level_fn: Any = _extract_packet_battery_level,
    extract_reply_id_fn: Any = _extract_reply_id,
    extract_emoji_codepoint_fn: Any = _extract_emoji_codepoint,
    emoji_from_codepoint_fn: Any = _emoji_from_codepoint,
    utc_now_fn: Any = _utc_now,
    format_epoch_fn: Any = _format_epoch,
    to_jsonable_fn: Any = _to_jsonable,
) -> None:
    record_tracker_packet_unlocked_fn(
        packet=packet,
        interface=interface,
        include_live_count=include_live_count,
        session_edges=tracker.edges,
        historical_edges=tracker._historical_edges,
        port_counts=tracker.port_counts,
        recent_packets=tracker.recent_packets,
        recent_chat=tracker.recent_chat,
        history_store=tracker._history_store,
        extract_delivery_update_fn=tracker._extract_delivery_update_fn,
        set_delivery_state_fn=tracker._set_delivery_state_fn,
        apply_tracker_observation_fn=apply_tracker_observation_fn,
        apply_routing_delivery_update_fn=apply_routing_delivery_update_fn,
        record_direct_edge_observation_fn=record_direct_edge_observation_fn,
        build_tracker_packet_artifacts_fn=build_tracker_packet_artifacts_fn,
        build_packet_summary_fn=build_packet_summary_fn,
        build_chat_entry_from_packet_fn=build_chat_entry_from_packet_fn,
        apply_tracker_storage_updates_fn=apply_tracker_storage_updates_fn,
        parse_tracker_packet_fn=parse_tracker_packet_fn,
        process_parsed_tracker_packet_fn=process_parsed_tracker_packet_fn,
        get_node_id_from_num_fn=get_node_id_from_num_fn,
        to_int_fn=to_int_fn,
        calculate_hops_fn=calculate_hops_fn,
        extract_packet_position_fn=extract_packet_position_fn,
        extract_packet_battery_level_fn=extract_packet_battery_level_fn,
        extract_reply_id_fn=extract_reply_id_fn,
        extract_emoji_codepoint_fn=extract_emoji_codepoint_fn,
        emoji_from_codepoint_fn=emoji_from_codepoint_fn,
        utc_now_fn=utc_now_fn,
        format_epoch_fn=format_epoch_fn,
        to_jsonable_fn=to_jsonable_fn,
    )
    tracker._expire_pending_deliveries_fn()


def record_tracker_receive_unlocked_for_tracker(
    tracker: Any,
    *,
    packet: Dict[str, Any],
    interface: Any,
    include_live_count: bool,
    get_node_id_from_num_fn: Any,
    record_tracker_packet_unlocked_fn: Any = _record_tracker_packet_unlocked_helper,
) -> None:
    record_tracker_receive_unlocked(
        tracker,
        packet=packet,
        interface=interface,
        include_live_count=include_live_count,
        get_node_id_from_num_fn=lambda iface, node_num: _resolve_tracker_node_id_from_num(
            iface,
            node_num,
            get_node_id_from_num_fn=get_node_id_from_num_fn,
        ),
        record_tracker_packet_unlocked_fn=record_tracker_packet_unlocked_fn,
    )
