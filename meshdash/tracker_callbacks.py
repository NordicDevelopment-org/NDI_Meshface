import time
from collections.abc import Reversible
from dataclasses import dataclass
from typing import Callable, Optional

from .runtime_types import (
    ExtractDeliveryUpdateFn,
    GetTimeoutSecondsFn,
    NowUnixFn,
    ParseUtcTextToUnixFn,
    SetDeliveryStateFn,
    ToIntFn,
    UtcNowFn,
)
from .tracker_storage_contracts import TrackerHistoryWriter
from .tracker_delivery_state import (
    expire_tracker_pending_deliveries as _expire_tracker_pending_deliveries_helper,
    extract_tracker_delivery_update as _extract_tracker_delivery_update_helper,
    set_tracker_delivery_state as _set_tracker_delivery_state_helper,
)


@dataclass(frozen=True)
class TrackerDeliveryCallbacks:
    set_delivery_state: SetDeliveryStateFn
    extract_delivery_update: ExtractDeliveryUpdateFn
    expire_pending_deliveries: Callable[[], None]


def build_tracker_delivery_callbacks(
    recent_chat: Reversible[object],
    *,
    history_store: TrackerHistoryWriter | None = None,
    get_timeout_seconds_fn: GetTimeoutSecondsFn,
    to_int_fn: ToIntFn,
    parse_utc_text_to_unix_fn: ParseUtcTextToUnixFn,
    utc_now_fn: UtcNowFn,
    now_unix_fn: NowUnixFn = time.time,
) -> TrackerDeliveryCallbacks:
    def _persist_delivery_update(entry: dict[str, object]) -> None:
        if history_store is None or not isinstance(entry, dict):
            return
        try:
            history_store.update_chat(entry)
        except Exception:
            return

    def _set_delivery_state(message_id: object, state: str, error: Optional[str] = None) -> bool:
        return _set_tracker_delivery_state_helper(
            recent_chat,
            message_id=message_id,
            state=state,
            error=error,
            to_int_fn=to_int_fn,
            utc_now_fn=utc_now_fn,
            now_unix_fn=now_unix_fn,
            on_update_fn=_persist_delivery_update,
        )

    def _extract_delivery_update(decoded: object) -> Optional[dict[str, object]]:
        return _extract_tracker_delivery_update_helper(decoded, to_int_fn=to_int_fn)

    def _expire_pending_deliveries() -> None:
        _expire_tracker_pending_deliveries_helper(
            recent_chat,
            timeout_seconds=int(get_timeout_seconds_fn()),
            to_int_fn=to_int_fn,
            parse_utc_text_to_unix_fn=parse_utc_text_to_unix_fn,
            utc_now_fn=utc_now_fn,
            now_unix_fn=now_unix_fn,
            on_expire_fn=_persist_delivery_update,
        )

    return TrackerDeliveryCallbacks(
        set_delivery_state=_set_delivery_state,
        extract_delivery_update=_extract_delivery_update,
        expire_pending_deliveries=_expire_pending_deliveries,
    )
