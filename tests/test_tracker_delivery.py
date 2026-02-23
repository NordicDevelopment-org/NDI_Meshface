from meshdash.tracker_delivery import apply_routing_delivery_update


def test_apply_routing_delivery_update_returns_false_when_no_update():
    called = []

    result = apply_routing_delivery_update(
        decoded={"portnum": "TEXT_MESSAGE_APP"},
        extract_update_fn=lambda _decoded: None,
        set_delivery_state_fn=lambda *_args: called.append(True) or True,
    )

    assert result is False
    assert called == []


def test_apply_routing_delivery_update_forwards_request_state_and_error():
    calls = []

    result = apply_routing_delivery_update(
        decoded={"routing": {"requestId": 123}},
        extract_update_fn=lambda _decoded: {
            "request_id": 123,
            "state": "acked",
            "error": None,
        },
        set_delivery_state_fn=lambda message_id, state, error: calls.append(
            (message_id, state, error)
        )
        or True,
    )

    assert result is True
    assert calls == [(123, "acked", None)]


def test_apply_routing_delivery_update_defaults_missing_state_to_sent():
    calls = []

    result = apply_routing_delivery_update(
        decoded={"routing": {"requestId": 123}},
        extract_update_fn=lambda _decoded: {"request_id": 123, "error": "NO_RESPONSE"},
        set_delivery_state_fn=lambda message_id, state, error: calls.append(
            (message_id, state, error)
        )
        or True,
    )

    assert result is True
    assert calls == [(123, "sent", "NO_RESPONSE")]
