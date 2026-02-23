import time
from typing import Any, Callable, Dict, Optional

from .helpers import to_int
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
