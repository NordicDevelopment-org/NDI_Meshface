from meshdash.api_system import handle_state_get


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
