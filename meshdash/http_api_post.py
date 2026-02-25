from typing import Any
from urllib.parse import urlparse

from .api_input_chat import parse_chat_send_request, validate_content_length
from .helpers import to_int
from .http_responses import write_json_response
from .http_route_contracts import DashboardPostRouteDependencies, SendChatFn, ToIntFn
from .http_routes import handle_dashboard_post


def build_post_route_dependencies(
    *,
    send_chat_fn: SendChatFn | None,
    to_int_fn: ToIntFn = to_int,
) -> DashboardPostRouteDependencies:
    return DashboardPostRouteDependencies(
        send_chat_fn=send_chat_fn,
        to_int_fn=to_int_fn,
        validate_content_length_fn=validate_content_length,
        parse_chat_send_request_fn=parse_chat_send_request,
        write_json_response_fn=write_json_response,
    )


def dispatch_post_request(
    handler: Any,
    *,
    deps: DashboardPostRouteDependencies,
    parse_url_fn=urlparse,
    handle_post_fn=handle_dashboard_post,
) -> None:
    parsed = parse_url_fn(handler.path)
    handle_post_fn(
        handler,
        path=parsed.path,
        deps=deps,
    )


def make_post_dispatch(
    *,
    deps: DashboardPostRouteDependencies,
):
    def _dispatch_post(handler: Any) -> None:
        dispatch_post_request(handler, deps=deps)

    return _dispatch_post
