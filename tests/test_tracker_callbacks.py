from meshdash.tracker_callbacks import build_tracker_delivery_callbacks


def test_build_tracker_delivery_callbacks_wires_set_extract_and_expire():
    recent_chat = []
    callbacks = build_tracker_delivery_callbacks(
        recent_chat,
        get_timeout_seconds_fn=lambda: 15,
        to_int_fn=int,
        parse_utc_text_to_unix_fn=lambda _value: None,
        utc_now_fn=lambda: "2026-01-01 00:00:00Z",
        now_unix_fn=lambda: 100,
    )

    set_fn = callbacks["set_delivery_state"]
    extract_fn = callbacks["extract_delivery_update"]
    expire_fn = callbacks["expire_pending_deliveries"]

    recent_chat.append(
        {
            "message_id": 123,
            "local_echo": True,
            "ack_requested": True,
            "delivery_state": "pending",
            "delivery_updated_unix": 50,
        }
    )

    assert set_fn(123, "acked", None) is True
    assert recent_chat[0]["delivery_state"] == "acked"
    assert extract_fn({"portnum": "ROUTING_APP", "routing": {"requestId": 123, "errorReason": "NONE"}}) == {
        "request_id": 123,
        "state": "acked",
        "error": None,
    }

    recent_chat[0]["delivery_state"] = "pending"
    recent_chat[0]["delivery_updated_unix"] = 1
    expire_fn()
    assert recent_chat[0]["delivery_state"] == "timeout"
