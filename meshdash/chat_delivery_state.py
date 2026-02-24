import time
from typing import Any, Callable, Dict, Optional

from .helpers import to_int
from .nodes import utc_now


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
