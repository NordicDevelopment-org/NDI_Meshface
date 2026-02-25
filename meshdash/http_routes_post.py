from .api_chat import (
    handle_chat_send_post as _handle_chat_send_post_helper,
)
from .http_handler_contracts import DashboardHttpHandler
from .http_route_contracts import DashboardPostRouteDependencies


def handle_dashboard_post(
    handler: DashboardHttpHandler,
    *,
    path: str,
    deps: DashboardPostRouteDependencies,
) -> None:
    if path != "/api/chat/send":
        deps.write_json_response_fn(
            handler,
            status_code=404,
            payload_obj={"ok": False, "error": "Not Found"},
        )
        return

    _handle_chat_send_post_helper(
        handler,
        send_chat_fn=deps.send_chat_fn,
        to_int_fn=deps.to_int_fn,
        validate_content_length_fn=deps.validate_content_length_fn,
        parse_chat_send_request_fn=deps.parse_chat_send_request_fn,
        write_json_response_fn=deps.write_json_response_fn,
    )
