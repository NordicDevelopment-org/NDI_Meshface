from typing import Any, Optional


def record_tracker_local_chat(
    *,
    text: str,
    from_id: str,
    to_id: str,
    channel_index: int,
    message_id: Optional[int],
    reply_id: Optional[int],
    emoji: Optional[str],
    emoji_codepoint: Optional[int],
    is_reaction: bool,
    ack_requested: bool,
    retry_of: Optional[int],
    recent_chat: Any,
    history_store: Any,
    build_tracker_local_entry_fn: Any,
    append_local_chat_entry_fn: Any,
    build_local_chat_entry_fn: Any,
    utc_now_fn: Any,
    now_unix_fn: Any,
    to_int_fn: Any,
    emoji_from_codepoint_fn: Any,
) -> None:
    entry = build_tracker_local_entry_fn(
        text=text,
        from_id=from_id,
        to_id=to_id,
        channel_index=channel_index,
        message_id=message_id,
        reply_id=reply_id,
        emoji=emoji,
        emoji_codepoint=emoji_codepoint,
        is_reaction=is_reaction,
        ack_requested=ack_requested,
        retry_of=retry_of,
        build_local_chat_entry_fn=build_local_chat_entry_fn,
        utc_now_fn=utc_now_fn,
        now_unix_fn=now_unix_fn,
        to_int_fn=to_int_fn,
        emoji_from_codepoint_fn=emoji_from_codepoint_fn,
    )
    if entry is None:
        return
    append_local_chat_entry_fn(
        recent_chat=recent_chat,
        history_store=history_store,
        entry=entry,
    )
