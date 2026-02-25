from meshdash.runtime_callbacks import build_send_chat_loader, build_state_snapshot_loader
from meshdash.revision import RevisionInfo


def test_build_state_snapshot_loader_forwards_bound_context():
    captured = {}

    def _build_state_fn(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    state_fn = build_state_snapshot_loader(
        iface="iface",
        tracker="tracker",
        started_at=123.0,
        target="mesh-target",
        show_secrets=False,
        storage_probe_path="/tmp/db.sqlite3",
        revision_info=RevisionInfo(version="0.1.0", commit="abc", label="L", title="T"),
        build_state_fn=_build_state_fn,
    )
    result = state_fn()

    assert result == {"ok": True}
    assert captured["iface"] == "iface"
    assert captured["tracker"] == "tracker"
    assert captured["target"] == "mesh-target"
    assert captured["storage_probe_path"] == "/tmp/db.sqlite3"
    assert captured["revision_info"]["version"] == "0.1.0"


def test_build_send_chat_loader_forwards_all_parameters():
    captured = {}

    class _Tracker:
        def __init__(self):
            self.record_local_chat = lambda **kwargs: None

    tracker = _Tracker()

    def _send_chat_message_fn(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    send_chat_fn = build_send_chat_loader(
        iface="iface",
        tracker=tracker,
        send_lock="lock",
        send_chat_message_fn=_send_chat_message_fn,
        send_reaction_packet_fn="reaction_fn",
        get_local_node_id_fn=lambda iface: "!abcd1234",
        chat_max_bytes=220,
        normalize_single_emoji_fn="normalize_fn",
        to_int_fn="to_int_fn",
        utc_now_fn="utc_now_fn",
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
    assert captured["record_local_chat_fn"] is tracker.record_local_chat
    assert captured["chat_max_bytes"] == 220
    assert captured["normalize_single_emoji_fn"] == "normalize_fn"
    assert captured["to_int_fn"] == "to_int_fn"
    assert captured["now_text_fn"] == "utc_now_fn"
    assert captured["local_node_id_fn"]() == "!abcd1234"
