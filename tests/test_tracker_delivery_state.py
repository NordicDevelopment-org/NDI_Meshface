import time

from meshdash.tracker_delivery_state import (
    expire_tracker_pending_deliveries,
    extract_tracker_delivery_update,
    set_tracker_delivery_state,
)


def test_set_tracker_delivery_state_updates_pending_entry():
    recent_chat = [
        {
            "message_id": 101,
            "local_echo": True,
            "delivery_state": "pending",
            "delivery_updated_unix": int(time.time()) - 5,
        }
    ]
    changed = set_tracker_delivery_state(
        recent_chat,
        message_id=101,
        state="acked",
        to_int_fn=int,
        utc_now_fn=lambda: "now",
        now_unix_fn=lambda: 200,
    )
    assert changed is True
    assert recent_chat[0]["delivery_state"] == "acked"
    assert recent_chat[0]["delivery_updated_unix"] == 200


def test_extract_tracker_delivery_update_parses_routing_packet():
    decoded = {"portnum": "ROUTING_APP", "routing": {"requestId": 123, "errorReason": "NONE"}}
    assert extract_tracker_delivery_update(decoded, to_int_fn=int) == {
        "request_id": 123,
        "state": "acked",
        "error": None,
    }


def test_expire_tracker_pending_deliveries_marks_timeout():
    recent_chat = [
        {
            "message_id": 201,
            "local_echo": True,
            "ack_requested": True,
            "delivery_state": "pending",
            "delivery_updated_unix": 100,
        }
    ]
    expire_tracker_pending_deliveries(
        recent_chat,
        timeout_seconds=10,
        to_int_fn=int,
        parse_utc_text_to_unix_fn=lambda _value: None,
        utc_now_fn=lambda: "now",
        now_unix_fn=lambda: 200,
    )
    assert recent_chat[0]["delivery_state"] == "timeout"
    assert "No ACK received" in recent_chat[0]["delivery_error"]
