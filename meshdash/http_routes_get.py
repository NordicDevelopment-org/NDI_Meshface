from .api_history import (
    build_node_history_response as _build_node_history_response_helper,
    build_online_activity_response as _build_online_activity_response_helper,
)
from .api_system import (
    handle_state_get as _handle_state_get_helper,
)
from .http_handler_contracts import DashboardHttpHandler
from .http_route_contracts import DashboardGetRouteDependencies


def handle_dashboard_get(
    handler: DashboardHttpHandler,
    *,
    path: str,
    query: str,
    deps: DashboardGetRouteDependencies,
) -> None:
    if path in ("/", "/index.html"):
        deps.write_html_response_fn(handler, html_text=deps.html_text)
        return

    if path == "/api/state":
        _handle_state_get_helper(
            handler,
            state_fn=deps.state_fn,
            write_json_response_fn=deps.write_json_response_fn,
        )
        return

    if path == "/api/history/node":
        response_obj = _build_node_history_response_helper(
            query=query,
            node_history_fn=deps.node_history_fn,
            to_int_fn=deps.to_int_fn,
            parse_node_history_request_fn=deps.parse_node_history_request_fn,
            empty_node_history_fn=deps.empty_node_history_fn,
        )
        deps.write_json_response_fn(handler, status_code=200, payload_obj=response_obj, no_store=True)
        return

    if path == "/api/history/online":
        response_obj = _build_online_activity_response_helper(
            query=query,
            online_activity_fn=deps.online_activity_fn,
            default_node_history_hours=deps.default_node_history_hours,
            to_int_fn=deps.to_int_fn,
            parse_online_activity_request_fn=deps.parse_online_activity_request_fn,
            empty_online_activity_fn=deps.empty_online_activity_fn,
        )
        deps.write_json_response_fn(handler, status_code=200, payload_obj=response_obj, no_store=True)
        return

    deps.write_text_response_fn(handler, status_code=404, text="Not Found")
