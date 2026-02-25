from typing import Any, Callable, Optional

from .http_api_get import build_get_route_dependencies, make_get_dispatch
from .http_api_post import build_post_route_dependencies, make_post_dispatch
from .http_handler import build_dashboard_handler_class
from .helpers import to_int


def make_http_handler(
    html_text: str,
    state_fn: Callable[[], dict],
    node_history_fn: Optional[Callable[[str, Optional[int], Optional[int]], dict]] = None,
    online_activity_fn: Optional[Callable[[Optional[int]], dict]] = None,
    send_chat_fn: Optional[Callable[..., dict]] = None,
    default_node_history_hours: int = 72,
    to_int_fn: Callable[[Any], Optional[int]] = to_int,
):
    get_deps = build_get_route_dependencies(
        html_text=html_text,
        state_fn=state_fn,
        node_history_fn=node_history_fn,
        online_activity_fn=online_activity_fn,
        default_node_history_hours=default_node_history_hours,
        to_int_fn=to_int_fn,
    )
    post_deps = build_post_route_dependencies(
        send_chat_fn=send_chat_fn,
        to_int_fn=to_int_fn,
    )

    return build_dashboard_handler_class(
        dispatch_get_fn=make_get_dispatch(deps=get_deps),
        dispatch_post_fn=make_post_dispatch(deps=post_deps),
    )
