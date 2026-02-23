import time
from typing import Any, Dict, Optional

from .chat import (
    expire_pending_deliveries as _expire_pending_deliveries_helper,
    extract_routing_delivery_update as _extract_routing_delivery_update_helper,
    set_delivery_state as _set_delivery_state_helper,
)


def set_tracker_delivery_state(
    recent_chat: Any,
    *,
    message_id: Any,
    state: str,
    error: Optional[str] = None,
    to_int_fn,
    utc_now_fn,
    now_unix_fn=time.time,
) -> bool:
    return _set_delivery_state_helper(
        recent_chat,
        message_id=message_id,
        state=state,
        error=error,
        to_int_fn=to_int_fn,
        now_text_fn=utc_now_fn,
        now_unix_fn=lambda: int(now_unix_fn()),
    )


def extract_tracker_delivery_update(decoded: Any, *, to_int_fn) -> Optional[Dict[str, Any]]:
    return _extract_routing_delivery_update_helper(decoded, to_int_fn=to_int_fn)


def expire_tracker_pending_deliveries(
    recent_chat: Any,
    *,
    timeout_seconds: int,
    to_int_fn,
    parse_utc_text_to_unix_fn,
    utc_now_fn,
    now_unix_fn=time.time,
) -> None:
    _expire_pending_deliveries_helper(
        recent_chat,
        timeout_seconds=timeout_seconds,
        to_int_fn=to_int_fn,
        parse_utc_text_to_unix_fn=parse_utc_text_to_unix_fn,
        now_unix_fn=lambda: int(now_unix_fn()),
        now_text_fn=utc_now_fn,
    )
