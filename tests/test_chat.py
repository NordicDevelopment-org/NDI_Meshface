from meshdash.chat import (
    build_local_chat_entry,
    chat_message_id,
    expire_pending_deliveries,
    extract_routing_delivery_update,
    set_delivery_state,
)


def test_chat_message_id_accepts_all_key_variants():
    assert chat_message_id({"message_id": "101"}) == 101
    assert chat_message_id({"messageId": 102}) == 102
    assert chat_message_id({"packet_id": 103}) == 103
    assert chat_message_id({"packetId": "104"}) == 104
    assert chat_message_id({"packetId": "bad"}) is None


def test_build_local_chat_entry_tracks_ack_for_direct_message():
    entry = build_local_chat_entry(
        text="hello",
        from_id="!local",
        to_id="!peer",
        message_id=1234,
        ack_requested=True,
        now_text="2026-01-01 00:00:00Z",
        now_unix=1000,
    )
    assert entry is not None
    assert entry["delivery_state"] == "pending"
    assert entry["ack_requested"] is True
    assert entry["message_id"] == 1234


def test_build_local_chat_entry_marks_error_when_ack_missing_message_id():
    entry = build_local_chat_entry(
        text="hello",
        from_id="!local",
        to_id="!peer",
        message_id=None,
        ack_requested=True,
        now_text="2026-01-01 00:00:00Z",
        now_unix=1000,
    )
    assert entry is not None
    assert entry["delivery_state"] == "error"
    assert "delivery_error" in entry


def test_build_local_chat_entry_supports_reaction_without_text():
    entry = build_local_chat_entry(
        text="",
        from_id="!local",
        to_id="!peer",
        reply_id=555,
        emoji="👍",
        is_reaction=True,
        now_text="2026-01-01 00:00:00Z",
        now_unix=1000,
    )
    assert entry is not None
    assert entry["is_reaction"] is True
    assert entry["reply_id"] == 555
    assert entry["emoji"] == "👍"


def test_extract_routing_delivery_update_returns_acked_or_nak():
    ack = extract_routing_delivery_update(
        {"portnum": "ROUTING_APP", "routing": {"requestId": 777, "errorReason": "NONE"}}
    )
    assert ack == {"request_id": 777, "state": "acked", "error": None}

    nak = extract_routing_delivery_update(
        {"portnum": "ROUTING_APP", "routing": {"requestId": 778, "errorReason": "NO_RESPONSE"}}
    )
    assert nak == {"request_id": 778, "state": "nak", "error": "NO_RESPONSE"}


def test_set_delivery_state_updates_latest_matching_local_echo_entry():
    entries = [
        {"message_id": 123, "local_echo": True, "delivery_state": "pending"},
        {"message_id": 123, "local_echo": True, "delivery_state": "pending", "delivery_error": "x"},
    ]
    changed = set_delivery_state(
        entries,
        message_id=123,
        state="acked",
        error=None,
        now_text_fn=lambda: "2026-01-01 00:00:10Z",
        now_unix_fn=lambda: 1010,
    )
    assert changed is True
    assert entries[-1]["delivery_state"] == "acked"
    assert "delivery_error" not in entries[-1]
    assert entries[-1]["delivery_updated_unix"] == 1010


def test_expire_pending_deliveries_marks_timeout():
    entries = [
        {
            "local_echo": True,
            "ack_requested": True,
            "delivery_state": "pending",
            "delivery_updated_unix": 1000,
        }
    ]
    expire_pending_deliveries(
        entries,
        timeout_seconds=5,
        now_unix_fn=lambda: 1010,
        now_text_fn=lambda: "2026-01-01 00:00:10Z",
    )
    assert entries[0]["delivery_state"] == "timeout"
    assert "No ACK received" in entries[0]["delivery_error"]
