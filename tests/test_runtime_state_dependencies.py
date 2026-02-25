from meshdash.revision import RevisionInfo
from meshdash.runtime_state_contracts import StateSnapshotRuntimeDependencies
from meshdash.runtime_state_dependencies import (
    build_state_snapshot_runtime_dependencies_from_legacy_args,
)


def test_build_state_snapshot_runtime_dependencies_from_legacy_args_maps_fields():
    revision = RevisionInfo(version="0.1.0", commit="abc", label="L", title="T")
    sentinel = {
        "iface": object(),
        "tracker": object(),
        "started_at": 123.0,
        "target": "mesh-target",
        "show_secrets": False,
        "storage_probe_path": "/tmp/db.sqlite3",
    }
    deps = build_state_snapshot_runtime_dependencies_from_legacy_args(
        **sentinel,
        revision_info=revision,
    )

    assert isinstance(deps, StateSnapshotRuntimeDependencies)
    assert deps.iface is sentinel["iface"]
    assert deps.tracker is sentinel["tracker"]
    assert deps.started_at == 123.0
    assert deps.target == "mesh-target"
    assert deps.show_secrets is False
    assert deps.storage_probe_path == "/tmp/db.sqlite3"
    assert deps.revision_info is revision


def test_build_state_snapshot_runtime_dependencies_accepts_optional_storage_probe_path():
    revision = RevisionInfo(version="0.1.0", commit="abc", label="L", title="T")
    deps = build_state_snapshot_runtime_dependencies_from_legacy_args(
        iface=object(),
        tracker=object(),
        started_at=123.0,
        target="mesh-target",
        show_secrets=False,
        storage_probe_path=None,
        revision_info=revision,
    )

    assert deps.storage_probe_path is None
