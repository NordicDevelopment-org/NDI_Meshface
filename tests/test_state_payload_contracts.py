from meshdash.state_payload_contracts import (
    DashboardStatePayload,
    StateTrafficPayload,
    coerce_dashboard_state_payload,
    coerce_state_traffic_payload,
    normalize_state_payload_for_api,
)


def test_state_traffic_payload_as_dict():
    payload = StateTrafficPayload(
        edges=[{"from": "!a", "to": "!b"}],
        port_counts=[{"portnum": "TEXT_MESSAGE_APP", "count": 3}],
        recent_packets=[{"summary": {"id": 1}}],
        recent_chat=[{"text": "hello"}],
    )
    assert payload.as_dict() == {
        "edges": [{"from": "!a", "to": "!b"}],
        "port_counts": [{"portnum": "TEXT_MESSAGE_APP", "count": 3}],
        "recent_packets": [{"summary": {"id": 1}}],
        "recent_chat": [{"text": "hello"}],
    }


def test_dashboard_state_payload_as_dict():
    payload = DashboardStatePayload(
        generated_at="2026-02-25T00:00:00Z",
        summary={"ok": True},
        summary_error=None,
        my_info={"id": "!a"},
        my_info_error=None,
        metadata={"board": "x1"},
        metadata_error=None,
        local_state={"local_config": {}},
        local_state_error=None,
        nodes_error=None,
        tracker_error=None,
        tracker_saved_counts_error=None,
        tracker_capabilities_error=None,
        nodes=[{"id": "!a"}],
        history_caps={"!a": {"gps_capable": True}},
        nodes_full=[{"id": "!a", "info": {}}],
        traffic=StateTrafficPayload(
            edges=[{"from": "!a", "to": "!b"}],
            port_counts=[{"portnum": "TEXT_MESSAGE_APP", "count": 3}],
            recent_packets=[{"summary": {"id": 1}}],
            recent_chat=[{"text": "hello"}],
        ),
    )

    out = payload.as_dict()
    assert out["generated_at"] == "2026-02-25T00:00:00Z"
    assert out["summary"]["ok"] is True
    assert out["summary_error"] is None
    assert out["nodes"][0]["id"] == "!a"
    assert out["traffic"]["edges"][0]["from"] == "!a"
    assert out["local_node_id"] == "local"


def test_coerce_state_traffic_payload_accepts_legacy_mapping():
    out = coerce_state_traffic_payload(
        {
            "edges": [{"from": "!a", "to": "!b"}],
            "port_counts": [{"portnum": "TEXT_MESSAGE_APP", "count": 3}],
            "recent_packets": [{"summary": {"id": 1}}],
            "recent_chat": [{"text": "hello"}],
        }
    )
    assert isinstance(out, StateTrafficPayload)
    assert out.edges[0]["from"] == "!a"


def test_coerce_dashboard_state_payload_accepts_legacy_mapping():
    out = coerce_dashboard_state_payload(
        {
            "generated_at": "2026-02-25T00:00:00Z",
            "summary": {"ok": True},
            "my_info": {"id": "!a"},
            "metadata": {"board": "x1"},
            "local_state": {"local_config": {}},
            "nodes": [{"id": "!a"}],
            "history_caps": {"!a": {"gps_capable": True}},
            "nodes_full": [{"id": "!a", "info": {}}],
            "traffic": {
                "edges": [{"from": "!a", "to": "!b"}],
                "port_counts": [{"portnum": "TEXT_MESSAGE_APP", "count": 3}],
                "recent_packets": [{"summary": {"id": 1}}],
                "recent_chat": [{"text": "hello"}],
            },
        }
    )
    assert isinstance(out, DashboardStatePayload)
    assert out.generated_at == "2026-02-25T00:00:00Z"
    assert out.summary["ok"] is True
    assert out.summary_error is None
    assert out.traffic.recent_chat[0]["text"] == "hello"
    assert out.local_node_id == "local"


def test_coerce_dashboard_state_payload_accepts_explicit_local_node_id():
    out = coerce_dashboard_state_payload(
        {
            "generated_at": "2026-02-25T00:00:00Z",
            "summary": {"ok": True},
            "traffic": {"edges": [], "port_counts": [], "recent_packets": [], "recent_chat": []},
            "local_node_id": "!49b54790",
        }
    )
    assert out.local_node_id == "!49b54790"


def test_normalize_state_payload_for_api_passthrough_for_non_dashboard_mapping():
    payload = {"ok": True, "count": 3}
    out = normalize_state_payload_for_api(payload)
    assert out == {"ok": True, "count": 3}


def test_normalize_state_payload_for_api_converts_dashboard_mapping_shape():
    payload = {
        "generated_at": "2026-02-25T00:00:00Z",
        "summary": {"ok": True},
        "traffic": {"edges": [], "port_counts": [], "recent_packets": [], "recent_chat": []},
    }
    out = normalize_state_payload_for_api(payload)
    assert out["generated_at"] == "2026-02-25T00:00:00Z"
    assert out["summary"]["ok"] is True
    assert out["traffic"]["recent_chat"] == []
