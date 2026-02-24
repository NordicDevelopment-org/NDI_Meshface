from typing import Any, Callable, Optional


def build_send_chat_loader(
    *,
    iface: Any,
    tracker: Any,
    send_lock: Any,
    send_chat_message_fn: Callable[..., dict],
    send_reaction_packet_fn: Callable[..., Any],
    get_local_node_id_fn: Callable[[Any], str],
    chat_max_bytes: int,
    normalize_single_emoji_fn: Callable[[Any], tuple[Optional[str], Optional[int]]],
    to_int_fn: Callable[[Any], Optional[int]],
    utc_now_fn: Callable[[], str],
) -> Callable[..., dict]:
    def send_chat_fn(
        text: Any,
        destination: Any = None,
        channel_index: Optional[int] = None,
        reply_id: Optional[int] = None,
        retry_of: Optional[int] = None,
        emoji: Any = None,
    ) -> dict:
        return send_chat_message_fn(
            text=text,
            destination=destination,
            channel_index=channel_index,
            reply_id=reply_id,
            retry_of=retry_of,
            emoji=emoji,
            iface=iface,
            send_lock=send_lock,
            send_reaction_packet_fn=send_reaction_packet_fn,
            local_node_id_fn=lambda: get_local_node_id_fn(iface),
            record_local_chat_fn=tracker.record_local_chat,
            chat_max_bytes=chat_max_bytes,
            normalize_single_emoji_fn=normalize_single_emoji_fn,
            to_int_fn=to_int_fn,
            now_text_fn=utc_now_fn,
        )

    return send_chat_fn
