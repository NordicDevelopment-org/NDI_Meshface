from typing import Any, Callable, Optional


def build_node_history_response(
    *,
    query: str,
    node_history_fn: Optional[Callable[[str, Optional[int], Optional[int]], dict]],
    to_int_fn: Callable[[Any], Optional[int]],
    parse_node_history_query_fn: Callable[..., tuple[str, Optional[int], Optional[int]]],
    empty_node_history_fn: Callable[[str], dict],
) -> dict:
    node_id, hours_override, points_override = parse_node_history_query_fn(
        query,
        to_int_fn=to_int_fn,
    )
    if node_history_fn is None:
        return empty_node_history_fn(node_id)
    return node_history_fn(node_id, hours_override, points_override)


def build_online_activity_response(
    *,
    query: str,
    online_activity_fn: Optional[Callable[[Optional[int]], dict]],
    default_node_history_hours: int,
    to_int_fn: Callable[[Any], Optional[int]],
    parse_online_activity_query_fn: Callable[..., Optional[int]],
    empty_online_activity_fn: Callable[[int], dict],
) -> dict:
    hours_override = parse_online_activity_query_fn(
        query,
        to_int_fn=to_int_fn,
    )
    if online_activity_fn is None:
        clean_hours = (
            hours_override
            if isinstance(hours_override, int) and hours_override > 0
            else default_node_history_hours
        )
        return empty_online_activity_fn(clean_hours)
    return online_activity_fn(hours_override)
