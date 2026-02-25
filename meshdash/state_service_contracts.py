from typing import Any, Optional, Protocol

from .revision import RevisionInfo
from .state_node_contracts import CollectedNodes, NodeByIdMap
from .tracker_snapshot_contracts import TrackerSnapshot

RevisionPayload = RevisionInfo | dict[str, str]


class CollectNodesFn(Protocol):
    def __call__(self, iface: Any) -> CollectedNodes | dict[str, Any]:
        ...


class CollectLocalStateFn(Protocol):
    def __call__(self, iface: Any) -> dict[str, Any]:
        ...


class CollectLocalStateSafeFn(Protocol):
    def __call__(
        self,
        iface: Any,
        *,
        collect_local_state_fn: CollectLocalStateFn,
    ) -> tuple[dict[str, Any], Optional[str]]:
        ...


class ModemPresetFromLocalStateFn(Protocol):
    def __call__(self, local_state: dict[str, Any]) -> Optional[str]:
        ...


class ApplyNodeSavedCountsFn(Protocol):
    def __call__(
        self,
        rows: list[dict[str, Any]],
        node_saved_counts: dict[str, dict[str, Any]],
    ) -> None:
        ...


class BuildSummaryPayloadFn(Protocol):
    def __call__(
        self,
        *,
        target: str,
        started_at: float,
        node_rows: list[dict[str, Any]],
        nodes_with_position: int,
        tracker_data: TrackerSnapshot | dict[str, Any],
        storage_probe_path: Optional[str],
        revision_info: RevisionPayload,
        modem_preset: Optional[str],
    ) -> dict[str, Any]:
        ...


class RedactSecretsFn(Protocol):
    def __call__(self, state: Any, sensitive_field_names: set[str]) -> Any:
        ...


class StateTracker(Protocol):
    def snapshot(self, by_id: dict[str, dict[str, Any]]) -> TrackerSnapshot | dict[str, Any]:
        ...

    def load_node_saved_counts(self) -> dict[str, dict[str, Any]]:
        ...

    def load_node_capabilities(self) -> dict[str, dict[str, Any]]:
        ...


class LoadTrackerSnapshotSafeFn(Protocol):
    def __call__(
        self,
        tracker: StateTracker,
        nodes_by_id: NodeByIdMap,
    ) -> tuple[TrackerSnapshot, Optional[str]]:
        ...


class LoadTrackerNodeSavedCountsSafeFn(Protocol):
    def __call__(
        self,
        tracker: StateTracker,
    ) -> tuple[dict[str, dict[str, Any]], Optional[str]]:
        ...


class LoadTrackerNodeCapabilitiesSafeFn(Protocol):
    def __call__(
        self,
        tracker: StateTracker,
    ) -> tuple[dict[str, dict[str, Any]], Optional[str]]:
        ...
