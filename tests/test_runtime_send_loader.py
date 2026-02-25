from meshdash.runtime_send_contracts import SendChatRuntimeDependencies
from meshdash.runtime_send_loader import build_send_chat_loader_with_dependencies


def test_build_send_chat_loader_with_dependencies_forwards_all_fields():
    captured = {}

    def _send_chat_message_fn(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    dependencies = SendChatRuntimeDependencies(
        iface="iface",
        send_lock="lock",
        send_reaction_packet_fn="reaction_fn",
        local_node_id_fn=lambda: "!abcd1234",
        record_local_chat_fn=lambda **_kwargs: None,
        chat_max_bytes=220,
        normalize_single_emoji_fn="normalize_fn",
        to_int_fn="to_int_fn",
        utc_now_fn="utc_now_fn",
    )

    send_chat_fn = build_send_chat_loader_with_dependencies(
        send_chat_message_fn=_send_chat_message_fn,
        dependencies=dependencies,
    )
    result = send_chat_fn(
        text="hello",
        destination="!dest0001",
        channel_index=2,
        reply_id=99,
        retry_of=1,
        emoji="😀",
    )

    assert result == {"ok": True}
    assert captured["text"] == "hello"
    assert captured["destination"] == "!dest0001"
    assert captured["channel_index"] == 2
    assert captured["reply_id"] == 99
    assert captured["retry_of"] == 1
    assert captured["emoji"] == "😀"
    assert captured["iface"] == "iface"
    assert captured["send_lock"] == "lock"
    assert captured["send_reaction_packet_fn"] == "reaction_fn"
    assert captured["chat_max_bytes"] == 220
    assert captured["normalize_single_emoji_fn"] == "normalize_fn"
    assert captured["to_int_fn"] == "to_int_fn"
    assert captured["now_text_fn"] == "utc_now_fn"
    assert captured["local_node_id_fn"]() == "!abcd1234"
