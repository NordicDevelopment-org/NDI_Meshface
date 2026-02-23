from meshdash.tracker_local_entry import build_tracker_local_entry


def test_build_tracker_local_entry_wires_time_and_fields_to_chat_builder():
    captured = {}

    def _build_local_chat_entry(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    entry = build_tracker_local_entry(
        text="hello",
        from_id="!a",
        to_id="!b",
        channel_index=2,
        message_id=101,
        reply_id=99,
        emoji="😀",
        emoji_codepoint=0x1F600,
        is_reaction=False,
        ack_requested=True,
        retry_of=3,
        build_local_chat_entry_fn=_build_local_chat_entry,
        utc_now_fn=lambda: "now-text",
        now_unix_fn=lambda: 123.9,
        to_int_fn=int,
        emoji_from_codepoint_fn=lambda cp: f"emoji-{cp}",
    )

    assert entry == {"ok": True}
    assert captured["text"] == "hello"
    assert captured["from_id"] == "!a"
    assert captured["to_id"] == "!b"
    assert captured["channel_index"] == 2
    assert captured["message_id"] == 101
    assert captured["reply_id"] == 99
    assert captured["emoji"] == "😀"
    assert captured["emoji_codepoint"] == 0x1F600
    assert captured["is_reaction"] is False
    assert captured["ack_requested"] is True
    assert captured["retry_of"] == 3
    assert captured["now_text"] == "now-text"
    assert captured["now_unix"] == 123
