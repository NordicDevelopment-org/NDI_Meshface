from dataclasses import dataclass
from typing import Any

from .revision import RevisionInfo


@dataclass(frozen=True)
class StateSnapshotRuntimeDependencies:
    iface: Any
    tracker: Any
    started_at: float
    target: str
    show_secrets: bool
    storage_probe_path: str
    revision_info: RevisionInfo
