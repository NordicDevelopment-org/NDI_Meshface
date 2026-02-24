from typing import Any, Dict, Optional

from .state_nodes import (
    collect_local_state as _collect_local_state_helper,
    collect_nodes as _collect_nodes_helper,
)
from .state_service import (
    build_dashboard_state as _build_dashboard_state_helper,
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
    return _build_dashboard_state_helper(
        iface=iface,
        tracker=tracker,
        started_at=started_at,
        target=target,
        show_secrets=show_secrets,
        storage_probe_path=storage_probe_path,
        revision_info=revision_info,
        sensitive_field_names=sensitive_field_names,
        collect_nodes_fn=collect_nodes,
        collect_local_state_fn=collect_local_state,
    )
