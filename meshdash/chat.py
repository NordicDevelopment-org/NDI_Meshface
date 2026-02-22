import time
from typing import Any, Callable, Dict, Optional

from .helpers import emoji_from_codepoint, to_int
from .nodes import parse_utc_text_to_unix, utc_now


def chat_message_id(entry: Any, *, to_int_fn: Callable[[Any], Optional[int]] = to_int) -> Optional[int]:
    if not isinstance(entry, dict):
        return None
    return to_int_fn(
        entry.get("message_id")
        or entry.get("messageId")
        or entry.get("packet_id")
        or entry.get("packetId")
    )


def set_delivery_state(
    recent_chat: Any,
    message_id: Any,
    state: str,
    error: Optional[str] = None,
    *,
    to_int_fn: Callable[[Any], Optional[int]] = to_int,
    now_text_fn: Callable[[], str] = utc_now,
    now_unix_fn: Callable[[], int] = lambda: int(time.time()),
) -> bool:
    clean_message_id = to_int_fn(message_id)
    if clean_message_id is None or clean_message_id <= 0:
        return False

    target: Optional[Dict[str, Any]] = None
    for entry in reversed(recent_chat):
        if not isinstance(entry, dict):
            continue
        if entry.get("local_echo") is not True:
            continue
        if chat_message_id(entry, to_int_fn=to_int_fn) != clean_message_id:
            continue
        target = entry
        break

    if target is None:
        return False

    target["delivery_state"] = str(state or "sent")
    target["delivery_updated_at"] = now_text_fn()
    target["delivery_updated_unix"] = now_unix_fn()
    if error:
        target["delivery_error"] = str(error)
    else:
        target.pop("delivery_error", None)
    return True


def extract_routing_delivery_update(
    decoded: Any,
    *,
    to_int_fn: Callable[[Any], Optional[int]] = to_int,
) -> Optional[Dict[str, Any]]:
    if not isinstance(decoded, dict):
        return None
    portnum = str(decoded.get("portnum") or "")
    if portnum != "ROUTING_APP":
        return None
    routing = decoded.get("routing")
    if not isinstance(routing, dict):
        return None

    request_id = (
        to_int_fn(routing.get("requestId"))
        or to_int_fn(routing.get("request_id"))
        or to_int_fn(decoded.get("requestId"))
        or to_int_fn(decoded.get("request_id"))
    )
    if request_id is None or request_id <= 0:
        return None

    error_reason = str(
        routing.get("errorReason")
        or routing.get("error_reason")
        or ""
    ).strip()
    if not error_reason or error_reason.upper() == "NONE":
        return {"request_id": request_id, "state": "acked", "error": None}
    return {"request_id": request_id, "state": "nak", "error": error_reason}


def expire_pending_deliveries(
    recent_chat: Any,
    timeout_seconds: int,
    *,
    to_int_fn: Callable[[Any], Optional[int]] = to_int,
    parse_utc_text_to_unix_fn: Callable[[Any], Optional[int]] = parse_utc_text_to_unix,
    now_unix_fn: Callable[[], int] = lambda: int(time.time()),
    now_text_fn: Callable[[], str] = utc_now,
) -> None:
    now_unix = now_unix_fn()
    timeout = max(1, int(timeout_seconds))
    for entry in recent_chat:
        if not isinstance(entry, dict):
            continue
        if entry.get("local_echo") is not True:
            continue
        if entry.get("ack_requested") is not True:
            continue
        if str(entry.get("delivery_state") or "") != "pending":
            continue

        pending_since = (
            to_int_fn(entry.get("delivery_updated_unix"))
            or parse_utc_text_to_unix_fn(entry.get("delivery_updated_at"))
            or parse_utc_text_to_unix_fn(entry.get("captured_at"))
            or parse_utc_text_to_unix_fn(entry.get("rx_time"))
        )
        if pending_since is None:
            pending_since = now_unix
            entry["delivery_updated_unix"] = pending_since
            entry["delivery_updated_at"] = now_text_fn()

        if now_unix - pending_since < timeout:
            continue

        entry["delivery_state"] = "timeout"
        entry["delivery_error"] = "No ACK received before timeout"
        entry["delivery_updated_unix"] = now_unix
        entry["delivery_updated_at"] = now_text_fn()


def build_local_chat_entry(
    text: Any,
    *,
    from_id: Any = "local",
    to_id: Any = "^all",
    channel_index: Any = 0,
    message_id: Any = None,
    reply_id: Any = None,
    emoji: Any = None,
    emoji_codepoint: Any = None,
    is_reaction: bool = False,
    ack_requested: bool = False,
    retry_of: Any = None,
    now_text: str,
    now_unix: int,
    to_int_fn: Callable[[Any], Optional[int]] = to_int,
    emoji_from_codepoint_fn: Callable[[Optional[int]], Optional[str]] = emoji_from_codepoint,
) -> Optional[Dict[str, Any]]:
    clean_text = str(text or "").strip()
    clean_message_id = to_int_fn(message_id)
    clean_reply_id = to_int_fn(reply_id)
    clean_emoji_codepoint = to_int_fn(emoji_codepoint)
    clean_emoji = str(emoji or "").strip() or emoji_from_codepoint_fn(clean_emoji_codepoint)
    if clean_emoji and clean_emoji_codepoint is None:
        clean_emoji_codepoint = ord(clean_emoji[0])
    has_reaction = bool(
        is_reaction or (clean_reply_id is not None and clean_reply_id > 0 and clean_emoji)
    )
    if not clean_text and not has_reaction:
        return None

    should_track_delivery = bool(ack_requested and not has_reaction and str(to_id or "^all") != "^all")
    delivery_state = "sent"
    delivery_error: Optional[str] = None
    if should_track_delivery:
        if clean_message_id is not None and clean_message_id > 0:
            delivery_state = "pending"
        else:
            delivery_state = "error"
            delivery_error = "Delivery tracking unavailable (missing packet id)"

    entry: Dict[str, Any] = {
        "captured_at": now_text,
        "from": str(from_id or "local"),
        "to": str(to_id or "^all"),
        "portnum": "TEXT_MESSAGE_APP",
        "channel": int(channel_index) if isinstance(channel_index, int) else 0,
        "rx_time": now_text,
        "text": clean_text,
        "local_echo": True,
        "delivery_state": delivery_state,
        "delivery_updated_at": now_text,
        "delivery_updated_unix": now_unix,
    }
    if clean_message_id is not None and clean_message_id > 0:
        entry["message_id"] = clean_message_id
    if clean_reply_id is not None and clean_reply_id > 0:
        entry["reply_id"] = clean_reply_id
    if clean_emoji:
        entry["emoji"] = clean_emoji
    if clean_emoji_codepoint is not None and clean_emoji_codepoint > 0:
        entry["emoji_codepoint"] = clean_emoji_codepoint
    if has_reaction:
        entry["is_reaction"] = True
    if should_track_delivery:
        entry["ack_requested"] = True
    if delivery_error:
        entry["delivery_error"] = delivery_error

    clean_retry_of = to_int_fn(retry_of)
    if clean_retry_of is not None and clean_retry_of > 0:
        entry["retry_of"] = clean_retry_of
    return entry
