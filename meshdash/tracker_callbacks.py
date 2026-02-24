import time
from dataclasses import dataclass
from typing import Any, Callable

from .tracker_delivery_state import (
    expire_tracker_pending_deliveries as _expire_tracker_pending_deliveries_helper,
    extract_tracker_delivery_update as _extract_tracker_delivery_update_helper,
    set_tracker_delivery_state as _set_tracker_delivery_state_helper,
)


@dataclass(frozen=True)
class TrackerDeliveryCallbacks:
    set_delivery_state: Callable[..., bool]
    extract_delivery_update: Callable[..., Any]
    expire_pending_deliveries: Callable[[], None]


def build_tracker_delivery_callbacks(
    recent_chat: Any,
    *,
    get_timeout_seconds_fn: Callable[[], int],
    to_int_fn,
    parse_utc_text_to_unix_fn,
    utc_now_fn,
    now_unix_fn=time.time,
) -> TrackerDeliveryCallbacks:
    def _set_delivery_state(message_id: Any, state: str, error: Any = None) -> bool:
        return _set_tracker_delivery_state_helper(
            recent_chat,
            message_id=message_id,
            state=state,
            error=error,
            to_int_fn=to_int_fn,
            utc_now_fn=utc_now_fn,
            now_unix_fn=now_unix_fn,
        )

    def _extract_delivery_update(decoded: Any):
        return _extract_tracker_delivery_update_helper(decoded, to_int_fn=to_int_fn)

    def _expire_pending_deliveries() -> None:
        _expire_tracker_pending_deliveries_helper(
            recent_chat,
            timeout_seconds=int(get_timeout_seconds_fn()),
            to_int_fn=to_int_fn,
            parse_utc_text_to_unix_fn=parse_utc_text_to_unix_fn,
            utc_now_fn=utc_now_fn,
            now_unix_fn=now_unix_fn,
        )

    return TrackerDeliveryCallbacks(
        set_delivery_state=_set_delivery_state,
        extract_delivery_update=_extract_delivery_update,
        expire_pending_deliveries=_expire_pending_deliveries,
    )
