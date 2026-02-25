from .http_route_contracts import (
    EmptyNodeHistoryFn,
    NodeHistoryFn,
    ParseNodeHistoryRequestFn,
    ToIntFn,
)


def build_node_history_response(
    *,
    query: str,
    node_history_fn: NodeHistoryFn | None,
    to_int_fn: ToIntFn,
    parse_node_history_request_fn: ParseNodeHistoryRequestFn,
    empty_node_history_fn: EmptyNodeHistoryFn,
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
