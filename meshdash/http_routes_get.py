from typing import Any, Callable, Optional

from .api_history import (
    build_node_history_response as _build_node_history_response_helper,
    build_online_activity_response as _build_online_activity_response_helper,
)
from .api_system import (
    handle_state_get as _handle_state_get_helper,
)


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
        _handle_state_get_helper(
            handler,
            state_fn=state_fn,
            write_json_response_fn=write_json_response_fn,
        )
        return

    if path == "/api/history/node":
        response_obj = _build_node_history_response_helper(
            query=query,
            node_history_fn=node_history_fn,
            to_int_fn=to_int_fn,
            parse_node_history_query_fn=parse_node_history_query_fn,
            empty_node_history_fn=empty_node_history_fn,
        )
        write_json_response_fn(handler, status_code=200, payload_obj=response_obj, no_store=True)
        return

    if path == "/api/history/online":
        response_obj = _build_online_activity_response_helper(
            query=query,
            online_activity_fn=online_activity_fn,
            default_node_history_hours=default_node_history_hours,
            to_int_fn=to_int_fn,
            parse_online_activity_query_fn=parse_online_activity_query_fn,
            empty_online_activity_fn=empty_online_activity_fn,
        )
        write_json_response_fn(handler, status_code=200, payload_obj=response_obj, no_store=True)
        return

    write_text_response_fn(handler, status_code=404, text="Not Found")
