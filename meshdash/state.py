from typing import Any, Dict, Optional

from .helpers import (
    redact_secrets,
    to_jsonable,
)
from .nodes import utc_now
from .state_nodes import (
    collect_local_state as _collect_local_state_helper,
    collect_nodes as _collect_nodes_helper,
)
from .state_summary import (
    apply_node_saved_counts as _apply_node_saved_counts_helper,
    build_summary_payload as _build_summary_payload_helper,
    collect_local_state_safe as _collect_local_state_safe_helper,
    modem_preset_from_local_state as _modem_preset_from_local_state_helper,
)


def collect_nodes(iface: Any) -> Dict[str, Any]:
    return _collect_nodes_helper(iface)


def collect_local_state(iface: Any) -> Dict[str, Any]:
    return _collect_local_state_helper(iface)


def build_state(
    iface: Any,
    tracker: Any,
    started_at: float,
    target: str,
    show_secrets: bool,
    storage_probe_path: Optional[str],
    revision_info: Dict[str, str],
    sensitive_field_names: set[str],
) -> Dict[str, Any]:
    nodes = collect_nodes(iface)
    tracker_data = tracker.snapshot(nodes["by_id"])
    node_saved_counts = tracker.load_node_saved_counts()
    node_capabilities = tracker.load_node_capabilities()
    _apply_node_saved_counts_helper(nodes["rows"], node_saved_counts)

    my_info = to_jsonable(getattr(iface, "myInfo", None))
    metadata = to_jsonable(getattr(iface, "metadata", None))

    local_state, local_error = _collect_local_state_safe_helper(
        iface,
        collect_local_state_fn=collect_local_state,
    )
    modem_preset = _modem_preset_from_local_state_helper(local_state)

    state = {
        "generated_at": utc_now(),
        "summary": _build_summary_payload_helper(
            target=target,
            started_at=started_at,
            node_rows=nodes["rows"],
            nodes_with_position=nodes["with_position_count"],
            tracker_data=tracker_data,
            storage_probe_path=storage_probe_path,
            revision_info=revision_info,
            modem_preset=modem_preset,
        ),
        "my_info": my_info,
        "metadata": metadata,
        "local_state": local_state,
        "local_state_error": local_error,
        "nodes": nodes["rows"],
        "history_caps": node_capabilities,
        "nodes_full": nodes["full"],
        "traffic": {
            "edges": tracker_data["edges"],
            "port_counts": tracker_data["port_counts"],
            "recent_packets": tracker_data["recent_packets"],
            "recent_chat": tracker_data["recent_chat"],
        },
    }

    if not show_secrets:
        state = redact_secrets(state, sensitive_field_names)

    return state
