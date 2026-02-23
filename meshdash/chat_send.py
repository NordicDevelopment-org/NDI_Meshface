from typing import Any, Callable, Dict, Optional


def prepare_chat_send_input(
    *,
    text: Any,
    destination: Any,
    channel_index: Optional[int],
    reply_id: Optional[int],
    retry_of: Optional[int],
    emoji: Any,
    chat_max_bytes: int,
    normalize_single_emoji_fn: Callable[[Any], tuple[Optional[str], Optional[int]]],
    to_int_fn: Callable[[Any], Optional[int]],
) -> Dict[str, Any]:
    clean_text = str(text or "").strip()
    clean_reply_id = to_int_fn(reply_id)
    clean_retry_of = to_int_fn(retry_of)
    clean_emoji, clean_emoji_codepoint = normalize_single_emoji_fn(emoji)

    has_reaction = bool(
        clean_reply_id is not None and clean_reply_id > 0 and clean_emoji and clean_emoji_codepoint
    )
    if clean_emoji and not has_reaction:
        raise ValueError("Emoji reactions require a valid reply_id")
    if clean_reply_id is not None and clean_reply_id <= 0:
        raise ValueError("reply_id must be a positive packet id")
    if has_reaction and clean_text:
        raise ValueError("Emoji reactions must not include text")
    if not clean_text and not has_reaction:
        raise ValueError("Message cannot be empty")

    if clean_text:
        payload_bytes = clean_text.encode("utf-8")
        if len(payload_bytes) > int(chat_max_bytes):
            raise ValueError(
                f"Message is too long ({len(payload_bytes)} bytes). Limit is {chat_max_bytes} bytes."
            )

    clean_destination = str(destination or "^all").strip() or "^all"
    if clean_destination.lower() in ("all", "broadcast"):
        clean_destination = "^all"
    if not (clean_destination == "^all" or clean_destination.startswith("!")):
        raise ValueError("Destination must be '^all' or a node id like !abcdef12")

    clean_channel = channel_index if isinstance(channel_index, int) and channel_index >= 0 else 0
    should_request_ack = bool(clean_destination != "^all" and not has_reaction)

    return {
        "text": clean_text,
        "reply_id": clean_reply_id,
        "retry_of": clean_retry_of,
        "emoji": clean_emoji,
        "emoji_codepoint": clean_emoji_codepoint,
        "is_reaction": has_reaction,
        "destination": clean_destination,
        "channel_index": clean_channel,
        "ack_requested": should_request_ack,
    }


def delivery_state_for_send(
    *,
    ack_requested: bool,
    sent_packet_id: Optional[int],
) -> str:
    if not ack_requested:
        return "sent"
    if sent_packet_id is not None and sent_packet_id > 0:
        return "pending"
    return "error"


def build_chat_send_response(
    *,
    now_text_fn: Callable[[], str],
    local_node_id: str,
    destination: str,
    channel_index: int,
    message_id: Optional[int],
    reply_id: Optional[int],
    retry_of: Optional[int],
    ack_requested: bool,
    delivery_state: str,
    text: str,
    is_reaction: bool,
    emoji: Optional[str],
    emoji_codepoint: Optional[int],
) -> Dict[str, Any]:
    response: Dict[str, Any] = {
        "ok": True,
        "sent_at": now_text_fn(),
        "from": local_node_id,
        "to": destination,
        "channel_index": channel_index,
        "message_id": message_id,
        "reply_id": reply_id,
        "ack_requested": ack_requested,
        "delivery_state": delivery_state,
    }
    if retry_of is not None and retry_of > 0:
        response["retry_of"] = retry_of
    if is_reaction:
        response["reaction"] = emoji
        response["reaction_codepoint"] = emoji_codepoint
        response["text"] = ""
    else:
        response["text"] = text
    return response
