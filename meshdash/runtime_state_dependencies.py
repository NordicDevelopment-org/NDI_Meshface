from typing import Any

from .revision import RevisionInfo
from .runtime_state_contracts import StateSnapshotRuntimeDependencies


def build_state_snapshot_runtime_dependencies_from_legacy_args(
    *,
    iface: Any,
    tracker: Any,
    started_at: float,
    target: str,
    show_secrets: bool,
    storage_probe_path: str,
    revision_info: RevisionInfo,
) -> StateSnapshotRuntimeDependencies:
    return StateSnapshotRuntimeDependencies(
        iface=iface,
        tracker=tracker,
        started_at=started_at,
        target=target,
        show_secrets=show_secrets,
        storage_probe_path=storage_probe_path,
        revision_info=revision_info,
    )
