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


def test_handle_state_get_lite_query_strips_heavy_fields_when_no_lite_builder():
    calls = {}
    payload = {
        "ok": True,
        "my_info": {"id": "!a"},
        "metadata": {"board": "x"},
        "local_state": {"local_config": {}},
        "nodes_full": [{"id": "!a"}],
        "nodes": [{"id": "!a"}],
    }
    handle_state_get(
        object(),
        state_fn=lambda: payload,
        write_json_response_fn=lambda handler, **kwargs: calls.update(kwargs),
        query="lite=true",
    )
    assert calls["status_code"] == 200
    assert "my_info" not in calls["payload_obj"]
    assert "metadata" not in calls["payload_obj"]
    assert "local_state" not in calls["payload_obj"]
    assert "nodes_full" not in calls["payload_obj"]
    assert calls["payload_obj"]["nodes"] == [{"id": "!a"}]


def test_handle_state_get_etag_304_and_fallback_header_iteration():
    calls = {"send_response": [], "send_header": [], "end_headers": 0}

    class _H:
        headers = {"if-none-match": "v1"}

        def send_response(self, code):
            calls["send_response"].append(code)

        def send_header(self, key, value):
            calls["send_header"].append((key, value))

        def end_headers(self):
            calls["end_headers"] += 1

    def _state():
        return {"ok": True}

    setattr(_state, "etag", lambda: "v1")

    handle_state_get(
        _H(),
        state_fn=_state,
        write_json_response_fn=lambda *_args, **_kwargs: calls.update({"write_called": True}),
        query="",
    )

    assert calls["send_response"] == [304]
    assert ("ETag", "v1") in calls["send_header"]
    assert ("Cache-Control", "no-store") in calls["send_header"]
    assert ("Content-Length", "0") in calls["send_header"]
    assert calls["end_headers"] == 1
    assert "write_called" not in calls


def test_handle_state_get_ignores_bad_etag_provider_and_bad_query_parse():
    calls = {}

    class _Headers:
        def get(self, _key):
            raise RuntimeError("bad headers")

        def items(self):
            return [("x", "y")]

    class _H:
        headers = _Headers()

    def _state():
        return {"ok": True, "count": 1}

    setattr(_state, "etag", lambda: (_ for _ in ()).throw(RuntimeError("etag fail")))

    handle_state_get(
        _H(),
        state_fn=_state,
        write_json_response_fn=lambda handler, **kwargs: calls.update(kwargs),
        query="%",
    )
    assert calls["status_code"] == 200
    assert calls["payload_obj"] == {"ok": True, "count": 1}
    assert "extra_headers" not in calls


def test_handle_state_get_includes_etag_for_non_matching_conditional_request():
    calls = {}

    class _BadKey:
        def __str__(self):
            raise RuntimeError("bad key")

    class _Headers:
        def get(self, _key):
            raise RuntimeError("direct lookup failed")

        def items(self):
            return [(_BadKey(), "x"), ("If-None-Match", "v0")]

    class _H:
        headers = _Headers()

    def _state():
        return {"ok": True}

    setattr(_state, "etag", lambda: "v1")

    handle_state_get(
        _H(),
        state_fn=_state,
        write_json_response_fn=lambda _handler, **kwargs: calls.update(kwargs),
        query="",
    )

    assert calls["status_code"] == 200
    assert calls["payload_obj"] == {"ok": True}
    assert calls["extra_headers"] == {"ETag": "v1"}


def test_handle_state_get_lite_query_with_non_mapping_payload_returns_payload_as_is():
    calls = {}

    handle_state_get(
        object(),
        state_fn=lambda: [1, 2, 3],
        write_json_response_fn=lambda _handler, **kwargs: calls.update(kwargs),
        query="lite=1",
    )

    assert calls["status_code"] == 200
    assert calls["payload_obj"] == [1, 2, 3]


def test_handle_state_get_handles_non_string_query_without_crashing():
    calls = {}

    handle_state_get(
        object(),
        state_fn=lambda: {"ok": True},
        write_json_response_fn=lambda _handler, **kwargs: calls.update(kwargs),
        query=object(),  # type: ignore[arg-type]
    )

    assert calls["status_code"] == 200
    assert calls["payload_obj"] == {"ok": True}
