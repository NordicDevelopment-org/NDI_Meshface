from meshdash.api_system import handle_state_get
from meshdash.state_payload_contracts import DashboardStatePayload, StateTrafficPayload


def test_handle_state_get_writes_state_payload():
    calls = {}

    handle_state_get(
        object(),
        state_fn=lambda: {"ok": True, "count": 3},
        write_json_response_fn=lambda handler, **kwargs: calls.update(kwargs),
    )

    assert calls == {
        "status_code": 200,
        "payload_obj": {"ok": True, "count": 3},
        "no_store": True,
    }


def test_handle_state_get_accepts_typed_state_payload():
    calls = {}
    typed = DashboardStatePayload(
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

    handle_state_get(
        object(),
        state_fn=lambda: typed,
        write_json_response_fn=lambda handler, **kwargs: calls.update(kwargs),
    )

    assert calls["status_code"] == 200
    assert calls["no_store"] is True
    assert calls["payload_obj"]["summary"]["ok"] is True
    assert calls["payload_obj"]["traffic"]["recent_chat"][0]["text"] == "hello"
    assert calls["payload_obj"]["local_node_id"] == "local"


def test_handle_state_get_prefers_lite_builder_when_available():
    calls = {}
    observed = {"full": 0, "lite": 0}

    def _state_fn():
        observed["full"] += 1
        return {"ok": True, "nodes_full": ["x"]}

    def _state_fn_lite():
        observed["lite"] += 1
        return {"ok": True}

    setattr(_state_fn, "lite", _state_fn_lite)

    handle_state_get(
        object(),
        state_fn=_state_fn,
        write_json_response_fn=lambda handler, **kwargs: calls.update(kwargs),
        query="lite=1",
    )

    assert observed["lite"] == 1
    assert observed["full"] == 0
    assert calls["status_code"] == 200
    assert calls["payload_obj"] == {"ok": True}
