from meshdash.state_tracker import (
    load_tracker_node_capabilities_safe,
    load_tracker_node_saved_counts_safe,
    load_tracker_snapshot_safe,
)


class _OkTracker:
    def snapshot(self, by_id):
        return {
            "live_packet_count": 2,
            "real_edge_count": 1,
            "edges": [{"from": "!a", "to": "!b"}],
            "port_counts": [{"portnum": "TEXT_MESSAGE_APP", "count": 3}],
            "recent_packets": [{"summary": {"id": 1}}],
            "recent_chat": [{"text": "hello"}],
        }

    def load_node_saved_counts(self):
        return {"!a": {"saved_packets": 2}}

    def load_node_capabilities(self):
        return {"!a": {"gps_capable": True}}


class _FailTracker:
    def snapshot(self, by_id):
        raise RuntimeError("snapshot failed")

    def load_node_saved_counts(self):
        raise RuntimeError("saved failed")

    def load_node_capabilities(self):
        raise RuntimeError("caps failed")


def test_load_tracker_snapshot_safe_success_path():
    out, error = load_tracker_snapshot_safe(_OkTracker(), {"!a": {"id": "!a"}})
    assert error is None
    assert out.live_packet_count == 2
    assert out.real_edge_count == 1
    assert out.edges[0]["from"] == "!a"


def test_load_tracker_snapshot_safe_failure_path_returns_empty_snapshot():
    out, error = load_tracker_snapshot_safe(_FailTracker(), {"!a": {"id": "!a"}})
    assert error == "snapshot failed"
    assert out.live_packet_count == 0
    assert out.real_edge_count == 0
    assert out.edges == []
    assert out.recent_chat == []


def test_load_tracker_node_saved_counts_safe_failure_path_returns_empty_mapping():
    out, error = load_tracker_node_saved_counts_safe(_FailTracker())
    assert error == "saved failed"
    assert out == {}


def test_load_tracker_node_capabilities_safe_failure_path_returns_empty_mapping():
    out, error = load_tracker_node_capabilities_safe(_FailTracker())
    assert error == "caps failed"
    assert out == {}
