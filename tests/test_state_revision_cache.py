from meshdash.revision import RevisionInfo
from meshdash.runtime_state_contracts import StateSnapshotRuntimeDependencies
from meshdash.runtime_state_loader import build_state_snapshot_loader_with_dependencies
from meshdash.tracker_runtime_impl import DashboardTracker


def _revision() -> RevisionInfo:
    return RevisionInfo(
        version="test",
        commit="test",
        label="test",
        title="Dashboard revision: test",
    )


class _Tracker:
    live_packet_count = 0
    radio_link_changed_unix = 0
    state_revision = 0


def test_state_snapshot_cache_key_includes_tracker_state_revision() -> None:
    tracker = _Tracker()
    calls = []

    def build_state_fn(**_kwargs):
        calls.append("full")
        return {"state_revision": tracker.state_revision}

    def build_lite_chat_fn(**_kwargs):
        calls.append("lite_chat")
        return {"state_revision": tracker.state_revision, "profile": "chat"}

    setattr(build_state_fn, "lite_chat", build_lite_chat_fn)
    state_fn = build_state_snapshot_loader_with_dependencies(
        dependencies=StateSnapshotRuntimeDependencies(
            iface=object(),
            tracker=tracker,
            started_at=0,
            target="test",
            show_secrets=False,
            storage_probe_path=None,
            revision_info=_revision(),
        ),
        build_state_fn=build_state_fn,
    )

    assert state_fn() == {"state_revision": 0}
    assert state_fn() == {"state_revision": 0}
    assert calls == ["full"]
    first_etag = state_fn.etag()  # type: ignore[attr-defined]

    tracker.state_revision += 1

    assert state_fn() == {"state_revision": 1}
    assert calls == ["full", "full"]
    assert state_fn.etag() != first_etag  # type: ignore[attr-defined]

    lite_chat_fn = state_fn.lite_chat  # type: ignore[attr-defined]
    assert lite_chat_fn() == {"state_revision": 1, "profile": "chat"}
    assert lite_chat_fn() == {"state_revision": 1, "profile": "chat"}
    assert calls == ["full", "full", "lite_chat"]

    tracker.state_revision += 1

    assert lite_chat_fn() == {"state_revision": 2, "profile": "chat"}
    assert calls == ["full", "full", "lite_chat", "lite_chat"]


def test_record_local_chat_bumps_tracker_state_revision() -> None:
    tracker = DashboardTracker(packet_limit=10)

    before = tracker.state_revision
    tracker.record_local_chat(
        text="hello",
        from_id="!local",
        to_id="^all",
        channel_index=0,
        message_id=123,
    )

    assert tracker.state_revision > before
