from typing import Any, Callable, Optional


def handle_dashboard_get(
    handler: Any,
    *,
    path: str,
    query: str,
    html_text: str,
    state_fn: Callable[[], dict],
    node_history_fn: Optional[Callable[[str, Optional[int], Optional[int]], dict]],
    online_activity_fn: Optional[Callable[[Optional[int]], dict]],
    default_node_history_hours: int,
    to_int_fn: Callable[[Any], Optional[int]],
    parse_node_history_query_fn: Callable[..., tuple[str, Optional[int], Optional[int]]],
    parse_online_activity_query_fn: Callable[..., Optional[int]],
    empty_node_history_fn: Callable[[str], dict],
    empty_online_activity_fn: Callable[[int], dict],
    write_html_response_fn: Callable[..., None],
    write_json_response_fn: Callable[..., None],
    write_text_response_fn: Callable[..., None],
) -> None:
    if path in ("/", "/index.html"):
        write_html_response_fn(handler, html_text=html_text)
        return

    if path == "/api/state":
        write_json_response_fn(handler, status_code=200, payload_obj=state_fn(), no_store=True)
        return

    if path == "/api/history/node":
        node_id, hours_override, points_override = parse_node_history_query_fn(
            query,
            to_int_fn=to_int_fn,
        )
        if node_history_fn is None:
            response_obj = empty_node_history_fn(node_id)
        else:
            response_obj = node_history_fn(node_id, hours_override, points_override)
        write_json_response_fn(handler, status_code=200, payload_obj=response_obj, no_store=True)
        return

    if path == "/api/history/online":
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
            response_obj = empty_online_activity_fn(clean_hours)
        else:
            response_obj = online_activity_fn(hours_override)
        write_json_response_fn(handler, status_code=200, payload_obj=response_obj, no_store=True)
        return

    write_text_response_fn(handler, status_code=404, text="Not Found")
