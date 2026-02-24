import meshdash.tracker_runtime_state as tracker_runtime_state
from meshdash.tracker_runtime_state import (
    build_tracker_snapshot,
    build_tracker_snapshot_for_tracker,
    load_tracker_node_capabilities,
    load_tracker_node_capabilities_for_tracker,
    load_tracker_node_saved_counts,
    load_tracker_node_saved_counts_for_tracker,
)


class _FakeHistoryStore:
    def __init__(self):
        self.saved_called = 0
        self.cap_called = 0

    def load_node_saved_counts(self):
        self.saved_called += 1
        return {"!a": {"saved": 2}}

    def load_node_capabilities(self):
        self.cap_called += 1
        return {"!a": {"gps_capable": True}}


def test_load_tracker_node_saved_counts_handles_none_store():
    assert load_tracker_node_saved_counts(None) == {}


def test_load_tracker_node_saved_counts_uses_store_reader():
    store = _FakeHistoryStore()
    result = load_tracker_node_saved_counts(store)
    assert result == {"!a": {"saved": 2}}
    assert store.saved_called == 1


def test_load_tracker_node_capabilities_handles_none_store():
    assert load_tracker_node_capabilities(None) == {}


def test_load_tracker_node_capabilities_uses_store_reader():
    store = _FakeHistoryStore()
    result = load_tracker_node_capabilities(store)
    assert result == {"!a": {"gps_capable": True}}
    assert store.cap_called == 1


def test_build_tracker_snapshot_expires_then_builds_payload():
    observed = {}

    def _expire():
        observed["expired"] = True

    def _build_payload(**kwargs):
        observed["payload_kwargs"] = kwargs
        return {"ok": True}

    session_edges = {("!a", "!b"): {"count": 1}}
    historical_edges = {("!a", "!b"): {"count": 5}}
    port_counts = {"TEXT_MESSAGE_APP": 3}
    recent_packets = [{"summary": {"id": 1}}]
    recent_chat = [{"text": "hello"}]
    nodes_by_id = {"!a": {"lat": 1.0, "lon": 2.0}}
    sentinel_format = object()
    sentinel_build_rows = object()

    payload = build_tracker_snapshot(
        nodes_by_id=nodes_by_id,
        expire_pending_deliveries_fn=_expire,
        session_edges=session_edges,
        historical_edges=historical_edges,
        port_counts=port_counts,
        recent_packets=recent_packets,
        recent_chat=recent_chat,
        live_packet_count=7,
        min_real_link_count=2,
        format_epoch_fn=sentinel_format,
        build_edge_snapshot_rows_fn=sentinel_build_rows,
        build_tracker_snapshot_payload_fn=_build_payload,
    )

    assert payload == {"ok": True}
    assert observed["expired"] is True
    assert observed["payload_kwargs"] == {
        "session_edges": session_edges,
        "historical_edges": historical_edges,
        "nodes_by_id": nodes_by_id,
        "port_counts": port_counts,
        "recent_packets": recent_packets,
        "recent_chat": recent_chat,
        "live_packet_count": 7,
        "min_real_link_count": 2,
        "format_epoch_fn": sentinel_format,
        "build_edge_snapshot_rows_fn": sentinel_build_rows,
    }


def test_load_tracker_node_saved_counts_for_tracker_uses_tracker_store(monkeypatch):
    observed = {}

    def _load(history_store):
        observed["history_store"] = history_store
        return {"!x": {"saved": 1}}

    monkeypatch.setattr(tracker_runtime_state, "load_tracker_node_saved_counts", _load)
    tracker = type("_Tracker", (), {"_history_store": "store"})()

    result = load_tracker_node_saved_counts_for_tracker(tracker)

    assert result == {"!x": {"saved": 1}}
    assert observed["history_store"] == "store"


def test_load_tracker_node_capabilities_for_tracker_uses_tracker_store(monkeypatch):
    observed = {}

    def _load(history_store):
        observed["history_store"] = history_store
        return {"!x": {"gps_capable": True}}

    monkeypatch.setattr(tracker_runtime_state, "load_tracker_node_capabilities", _load)
    tracker = type("_Tracker", (), {"_history_store": "store"})()

    result = load_tracker_node_capabilities_for_tracker(tracker)

    assert result == {"!x": {"gps_capable": True}}
    assert observed["history_store"] == "store"


def test_build_tracker_snapshot_for_tracker_uses_runtime_state(monkeypatch):
    observed = {}

    def _build_snapshot(**kwargs):
        observed["kwargs"] = kwargs
        return {"ok": True}

    monkeypatch.setattr(tracker_runtime_state, "build_tracker_snapshot", _build_snapshot)

    def _expire(self):
        pass

    tracker = type(
        "_Tracker",
        (),
        {
            "_expire_pending_deliveries_fn": _expire,
            "edges": {"e": 1},
            "_historical_edges": {"h": 2},
            "port_counts": {"TEXT_MESSAGE_APP": 3},
            "recent_packets": [{"summary": {"id": 1}}],
            "recent_chat": [{"text": "hello"}],
            "live_packet_count": 9,
        },
    )()
    nodes_by_id = {"!a": {"name": "A"}}
    sentinel_format = object()
    sentinel_build_rows = object()
    sentinel_build_payload = object()

    payload = build_tracker_snapshot_for_tracker(
        tracker,
        nodes_by_id=nodes_by_id,
        min_real_link_count=2,
        format_epoch_fn=sentinel_format,
        build_edge_snapshot_rows_fn=sentinel_build_rows,
        build_tracker_snapshot_payload_fn=sentinel_build_payload,
    )

    assert payload == {"ok": True}
    assert observed["kwargs"] == {
        "nodes_by_id": nodes_by_id,
        "expire_pending_deliveries_fn": tracker._expire_pending_deliveries_fn,
        "session_edges": {"e": 1},
        "historical_edges": {"h": 2},
        "port_counts": {"TEXT_MESSAGE_APP": 3},
        "recent_packets": [{"summary": {"id": 1}}],
        "recent_chat": [{"text": "hello"}],
        "live_packet_count": 9,
        "min_real_link_count": 2,
        "format_epoch_fn": sentinel_format,
        "build_edge_snapshot_rows_fn": sentinel_build_rows,
        "build_tracker_snapshot_payload_fn": sentinel_build_payload,
    }
