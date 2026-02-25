from meshdash.revision import RevisionInfo
from meshdash.runtime_state_contracts import StateSnapshotRuntimeDependencies
from meshdash.runtime_state_loader import build_state_snapshot_loader_with_dependencies


def test_build_state_snapshot_loader_with_dependencies_forwards_bound_context():
    captured = {}

    def _build_state_fn(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    dependencies = StateSnapshotRuntimeDependencies(
        iface="iface",
        tracker="tracker",
        started_at=123.0,
        target="mesh-target",
        show_secrets=False,
        storage_probe_path="/tmp/db.sqlite3",
        revision_info=RevisionInfo(version="0.1.0", commit="abc", label="L", title="T"),
    )

    state_fn = build_state_snapshot_loader_with_dependencies(
        dependencies=dependencies,
        build_state_fn=_build_state_fn,
    )
    result = state_fn()

    assert result == {"ok": True}
    assert captured["iface"] == "iface"
    assert captured["tracker"] == "tracker"
    assert captured["target"] == "mesh-target"
    assert captured["storage_probe_path"] == "/tmp/db.sqlite3"
    assert isinstance(captured["revision_info"], RevisionInfo)
    assert captured["revision_info"].version == "0.1.0"


def test_build_state_snapshot_loader_with_dependencies_allows_optional_storage_probe_path():
    captured = {}

    def _build_state_fn(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    dependencies = StateSnapshotRuntimeDependencies(
        iface="iface",
        tracker="tracker",
        started_at=123.0,
        target="mesh-target",
        show_secrets=False,
        storage_probe_path=None,
        revision_info=RevisionInfo(version="0.1.0", commit="abc", label="L", title="T"),
    )

    state_fn = build_state_snapshot_loader_with_dependencies(
        dependencies=dependencies,
        build_state_fn=_build_state_fn,
    )
    result = state_fn()

    assert result == {"ok": True}
    assert captured["storage_probe_path"] is None
