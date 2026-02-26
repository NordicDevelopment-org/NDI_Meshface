try:
    import meshtastic
except Exception:
    meshtastic = None

from .helpers import (
    to_int as _to_int,
)
from .nodes import (
    get_node_id_from_num as _get_node_id_from_num_helper,
)
from .tracker_node_resolver import (
    get_tracker_node_id_from_num as _get_tracker_node_id_from_num_helper,
)
from .tracker_runtime_receive import (
    record_tracker_receive_unlocked as _record_tracker_receive_unlocked_helper,
)
from .tracker_runtime_record import (
    record_tracker_packet_unlocked_with_dependencies as _record_tracker_packet_unlocked_with_dependencies_helper,
)
from .tracker_runtime_types import (
    TrackerReceiveRuntimeState,
)
from .runtime_types import (
    GetNodeIdFromNumFn,
    RecordTrackerPacketUnlockedFn,
    RecordTrackerPacketUnlockedWithDependenciesFn,
    RecordTrackerReceiveUnlockedFn,
    ResolveTrackerNodeIdFromNumFn,
    ToIntFn,
    TrackerPacket,
)


def _resolve_tracker_node_id_from_num(
    iface: object,
    node_num: object,
    *,
    meshtastic_module: object = meshtastic,
    to_int_fn: ToIntFn = _to_int,
    get_node_id_from_num_fn: GetNodeIdFromNumFn = _get_node_id_from_num_helper,
) -> str | None:
    try:
        return _get_tracker_node_id_from_num_helper(
            iface,
            node_num,
            meshtastic_module=meshtastic_module,
            to_int_fn=to_int_fn,
            get_node_id_from_num_fn=get_node_id_from_num_fn,
        )
    except Exception:
        return None


def record_tracker_receive_unlocked_for_tracker(
    tracker: TrackerReceiveRuntimeState,
    *,
    packet: TrackerPacket,
    interface: object,
    include_live_count: bool,
    get_node_id_from_num_fn: GetNodeIdFromNumFn = _get_node_id_from_num_helper,
    record_tracker_packet_unlocked_fn: RecordTrackerPacketUnlockedFn | None = None,
    record_tracker_packet_unlocked_with_dependencies_fn: RecordTrackerPacketUnlockedWithDependenciesFn = _record_tracker_packet_unlocked_with_dependencies_helper,
    resolve_tracker_node_id_from_num_fn: ResolveTrackerNodeIdFromNumFn = _resolve_tracker_node_id_from_num,
    record_tracker_receive_unlocked_fn: RecordTrackerReceiveUnlockedFn = _record_tracker_receive_unlocked_helper,
) -> None:
    record_tracker_receive_unlocked_fn(
        tracker,
        packet=packet,
        interface=interface,
        include_live_count=include_live_count,
        get_node_id_from_num_fn=lambda iface, node_num: resolve_tracker_node_id_from_num_fn(
            iface,
            node_num,
            get_node_id_from_num_fn=get_node_id_from_num_fn,
        ),
        record_tracker_packet_unlocked_fn=record_tracker_packet_unlocked_fn,
        record_tracker_packet_unlocked_with_dependencies_fn=record_tracker_packet_unlocked_with_dependencies_fn,
    )
