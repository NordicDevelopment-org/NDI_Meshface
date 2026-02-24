import meshdash.tracker_runtime_chat as tracker_runtime_chat
from meshdash.tracker_runtime_chat import record_tracker_local_chat


def test_record_tracker_local_chat_builds_and_appends_entry():
    observed = {}

    def _build_tracker_local_entry(**kwargs):
        observed["build_kwargs"] = kwargs
        return {"message_id": 9}

    def _append_local_chat_entry(**kwargs):
        observed["append_kwargs"] = kwargs

    recent_chat = []
    history_store = object()
    sentinel_build_local_chat_entry = object()
    sentinel_utc_now = object()
    sentinel_now_unix = object()
    sentinel_to_int = object()
    sentinel_emoji_from_codepoint = object()

    record_tracker_local_chat(
        text="hello",
        from_id="!a",
        to_id="!b",
        channel_index=2,
        message_id=123,
        reply_id=99,
        emoji="👍",
        emoji_codepoint=128077,
        is_reaction=True,
        ack_requested=True,
        retry_of=55,
        recent_chat=recent_chat,
        history_store=history_store,
        build_tracker_local_entry_fn=_build_tracker_local_entry,
        append_local_chat_entry_fn=_append_local_chat_entry,
        build_local_chat_entry_fn=sentinel_build_local_chat_entry,
        utc_now_fn=sentinel_utc_now,
        now_unix_fn=sentinel_now_unix,
        to_int_fn=sentinel_to_int,
        emoji_from_codepoint_fn=sentinel_emoji_from_codepoint,
    )

    assert observed["build_kwargs"] == {
        "text": "hello",
        "from_id": "!a",
        "to_id": "!b",
        "channel_index": 2,
        "message_id": 123,
        "reply_id": 99,
        "emoji": "👍",
        "emoji_codepoint": 128077,
        "is_reaction": True,
        "ack_requested": True,
        "retry_of": 55,
        "build_local_chat_entry_fn": sentinel_build_local_chat_entry,
        "utc_now_fn": sentinel_utc_now,
        "now_unix_fn": sentinel_now_unix,
        "to_int_fn": sentinel_to_int,
        "emoji_from_codepoint_fn": sentinel_emoji_from_codepoint,
    }
    assert observed["append_kwargs"] == {
        "recent_chat": recent_chat,
        "history_store": history_store,
        "entry": {"message_id": 9},
    }


def test_record_tracker_local_chat_skips_append_when_build_returns_none():
    observed = {}

    def _build_tracker_local_entry(**kwargs):
        observed["build_called"] = True
        return None

    def _append_local_chat_entry(**_kwargs):
        observed["append_called"] = True

    record_tracker_local_chat(
        text="hello",
        from_id="!a",
        to_id="!b",
        channel_index=0,
        message_id=None,
        reply_id=None,
        emoji=None,
        emoji_codepoint=None,
        is_reaction=False,
        ack_requested=False,
        retry_of=None,
        recent_chat=[],
        history_store=None,
        build_tracker_local_entry_fn=_build_tracker_local_entry,
        append_local_chat_entry_fn=_append_local_chat_entry,
        build_local_chat_entry_fn=object(),
        utc_now_fn=object(),
        now_unix_fn=object(),
        to_int_fn=object(),
        emoji_from_codepoint_fn=object(),
    )

    assert observed == {"build_called": True}


def test_record_tracker_local_chat_for_tracker_uses_tracker_context(monkeypatch):
    observed = {}

    def _record_tracker_local_chat(**kwargs):
        observed.update(kwargs)

    monkeypatch.setattr(
        tracker_runtime_chat, "record_tracker_local_chat", _record_tracker_local_chat
    )

    class _Tracker:
        def __init__(self):
            self.recent_chat = []
            self._history_store = "history-store"

    tracker = _Tracker()
    sentinel_now_unix = object()

    tracker_runtime_chat.record_tracker_local_chat_for_tracker(
        tracker,
        text="hello",
        from_id="!a",
        to_id="!b",
        channel_index=4,
        message_id=42,
        reply_id=7,
        emoji="👍",
        emoji_codepoint=128077,
        is_reaction=True,
        ack_requested=True,
        retry_of=3,
        now_unix_fn=sentinel_now_unix,
    )

    assert observed["text"] == "hello"
    assert observed["from_id"] == "!a"
    assert observed["to_id"] == "!b"
    assert observed["channel_index"] == 4
    assert observed["message_id"] == 42
    assert observed["reply_id"] == 7
    assert observed["emoji"] == "👍"
    assert observed["emoji_codepoint"] == 128077
    assert observed["is_reaction"] is True
    assert observed["ack_requested"] is True
    assert observed["retry_of"] == 3
    assert observed["recent_chat"] is tracker.recent_chat
    assert observed["history_store"] == "history-store"
    assert (
        observed["build_tracker_local_entry_fn"]
        is tracker_runtime_chat._build_tracker_local_entry_helper
    )
    assert (
        observed["append_local_chat_entry_fn"]
        is tracker_runtime_chat._append_local_chat_entry_helper
    )
    assert observed["build_local_chat_entry_fn"] is tracker_runtime_chat._build_local_chat_entry
    assert observed["utc_now_fn"] is tracker_runtime_chat._utc_now
    assert observed["now_unix_fn"] is sentinel_now_unix
    assert observed["to_int_fn"] is tracker_runtime_chat._to_int
    assert observed["emoji_from_codepoint_fn"] is tracker_runtime_chat._emoji_from_codepoint
