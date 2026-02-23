from meshdash.tracker_packet_artifacts import build_tracker_packet_artifacts


def test_build_tracker_packet_artifacts_builds_packet_and_chat_entries():
    packet = {"id": 7, "fromId": "!a"}
    parsed = {
        "decoded": {"portnum": "TEXT_MESSAGE_APP"},
        "from_id": "!a",
        "to_id": "!b",
        "packet_id": 7,
        "rx_time": 123,
        "hops": 2,
        "reply_id": 9,
        "emoji_glyph": "😀",
        "emoji_codepoint": 0x1F600,
        "is_reaction": False,
        "packet_position": {"lat": 44.9},
        "packet_battery": 88,
    }

    packet_entry, chat_entry = build_tracker_packet_artifacts(
        packet=packet,
        parsed=parsed,
        include_live_count=True,
        build_packet_summary_fn=lambda **kwargs: {
            "id": kwargs["packet_id"],
            "from": kwargs["from_id"],
            "to": kwargs["to_id"],
        },
        build_chat_entry_from_packet_fn=lambda **kwargs: {
            "message_id": kwargs["packet_id"],
            "text": "ok",
        },
        utc_now_fn=lambda: "now",
        format_epoch_fn=lambda v: f"t{v}",
        to_int_fn=int,
        to_jsonable_fn=lambda value: {"raw": value["id"]},
    )

    assert packet_entry == {
        "summary": {"id": 7, "from": "!a", "to": "!b", "live": True},
        "packet": {"raw": 7},
    }
    assert chat_entry == {"message_id": 7, "text": "ok"}
