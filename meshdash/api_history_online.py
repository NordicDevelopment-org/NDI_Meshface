from typing import Any

from .http_route_contracts import (
    EmptyOnlineActivityFn,
    OnlineActivityFn,
    ParseOnlineActivityRequestFn,
    ToIntFn,
)


def build_online_activity_response(
    *,
    query: str,
    online_activity_fn: OnlineActivityFn | None,
    default_node_history_hours: int,
    to_int_fn: ToIntFn,
    parse_online_activity_request_fn: ParseOnlineActivityRequestFn,
    empty_online_activity_fn: EmptyOnlineActivityFn,
) -> dict:
    query_obj = parse_online_activity_request_fn(
        query,
        to_int_fn=to_int_fn,
    )
    hours_override = query_obj.hours_override
    if online_activity_fn is None:
        clean_hours = (
            hours_override
            if isinstance(hours_override, int) and hours_override > 0
            else default_node_history_hours
        )
        return empty_online_activity_fn(clean_hours)
    return online_activity_fn(hours_override)
