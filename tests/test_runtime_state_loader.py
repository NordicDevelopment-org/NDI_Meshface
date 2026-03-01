from meshdash.revision import RevisionInfo
from meshdash.runtime_state_contracts import StateSnapshotRuntimeDependencies
from meshdash.runtime_state_loader import build_state_snapshot_loader_with_dependencies


class _TrackerWithRadioLinkRev:
    def __init__(self):
        self.live_packet_count = 0
        self.radio_link_changed_unix = 0


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


def test_build_state_snapshot_loader_cache_key_includes_radio_link_revision():
    tracker = _TrackerWithRadioLinkRev()
    build_calls = {"count": 0}

    def _build_state_fn(**kwargs):
        del kwargs
        build_calls["count"] += 1
        return {"ok": True, "count": build_calls["count"]}

    dependencies = StateSnapshotRuntimeDependencies(
        iface="iface",
        tracker=tracker,
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

    first = state_fn()
    second = state_fn()
    assert first["count"] == 1
    assert second["count"] == 1

    tracker.radio_link_changed_unix = 1234
    third = state_fn()
    assert third["count"] == 2

    etag_fn = getattr(state_fn, "etag", None)
    assert callable(etag_fn)
    etag = str(etag_fn())
    assert "-r1234-" in etag
