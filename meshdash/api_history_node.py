from typing import Any, Callable, Optional

from .api_input_history import NodeHistoryQuery


def build_node_history_response(
    *,
    query: str,
    node_history_fn: Optional[Callable[[str, Optional[int], Optional[int]], dict]],
    to_int_fn: Callable[[Any], Optional[int]],
    parse_node_history_request_fn: Callable[..., NodeHistoryQuery],
    empty_node_history_fn: Callable[[str], dict],
) -> dict:
    query_obj = parse_node_history_request_fn(
        query,
        to_int_fn=to_int_fn,
    )
    node_id = query_obj.node_id
    hours_override = query_obj.hours_override
    points_override = query_obj.points_override
    if node_history_fn is None:
        return empty_node_history_fn(node_id)
    return node_history_fn(node_id, hours_override, points_override)
