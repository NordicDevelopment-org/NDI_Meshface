from meshdash.tracker_snapshot_contracts import (
    TrackerSnapshot,
    coerce_tracker_snapshot,
    empty_tracker_snapshot,
)


def test_coerce_tracker_snapshot_passthrough_for_typed_contract():
    typed = TrackerSnapshot(
        live_packet_count=4,
        real_edge_count=2,
        edges=[{"from": "!a", "to": "!b"}],
        port_counts=[{"portnum": "TEXT_MESSAGE_APP", "count": 3}],
        recent_packets=[{"summary": {"id": 1}}],
        recent_chat=[{"text": "hello"}],
    )
    out = coerce_tracker_snapshot(typed)
    assert out is typed


def test_coerce_tracker_snapshot_accepts_legacy_mapping_shape():
    out = coerce_tracker_snapshot(
        {
            "live_packet_count": 4,
            "real_edge_count": 2,
            "edges": [{"from": "!a", "to": "!b"}],
            "port_counts": [{"portnum": "TEXT_MESSAGE_APP", "count": 3}],
            "recent_packets": [{"summary": {"id": 1}}],
            "recent_chat": [{"text": "hello"}],
        }
    )
    assert isinstance(out, TrackerSnapshot)
    assert out.live_packet_count == 4
    assert out.real_edge_count == 2
    assert out.edges[0]["from"] == "!a"
    assert out.port_counts[0]["portnum"] == "TEXT_MESSAGE_APP"
    assert out.recent_packets[0]["summary"]["id"] == 1
    assert out.recent_chat[0]["text"] == "hello"


def test_empty_tracker_snapshot_returns_zeroed_contract():
    out = empty_tracker_snapshot()
    assert isinstance(out, TrackerSnapshot)
    assert out.live_packet_count == 0
    assert out.real_edge_count == 0
    assert out.edges == []
    assert out.port_counts == []
    assert out.recent_packets == []
    assert out.recent_chat == []
