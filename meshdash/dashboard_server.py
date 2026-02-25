from dataclasses import dataclass
from typing import Any

from .revision import RevisionInfo
from .runtime_types import (
    MakeHttpHandlerFn,
    NodeHistoryFn,
    OnlineActivityFn,
    RenderHtmlFn,
    SendChatFn,
    StateFn,
    ThreadingHttpServerCls,
)


@dataclass(frozen=True)
class DashboardServerParts:
    server: Any
    html: str
    handler_cls: Any
    bound_host: str
    bound_port: int


def build_dashboard_server(
    *,
    args: Any,
    revision_info: RevisionInfo,
    history_enabled: bool,
    state_fn: StateFn,
    node_history_fn: NodeHistoryFn,
    online_activity_fn: OnlineActivityFn,
    send_chat_fn: SendChatFn,
    render_html_fn: RenderHtmlFn,
    make_http_handler_fn: MakeHttpHandlerFn,
    threading_http_server_cls: ThreadingHttpServerCls,
) -> DashboardServerParts:
    html = render_html_fn(
        refresh_ms=args.refresh_ms,
        packet_limit=args.packet_limit,
        show_secrets=args.show_secrets,
        history_enabled=history_enabled,
        history_max_rows=args.history_max_rows,
        history_retention_days=args.history_retention_days,
        node_history_hours=args.node_history_hours,
        node_history_max_points=args.node_history_max_points,
        revision_label=revision_info.label,
        revision_title=revision_info.title,
    )
    handler_cls = make_http_handler_fn(
        html,
        state_fn,
        node_history_fn=node_history_fn,
        online_activity_fn=online_activity_fn,
        send_chat_fn=send_chat_fn,
    )
    server = threading_http_server_cls((args.http_host, args.http_port), handler_cls)
    bound_host, bound_port = server.server_address[:2]
    return DashboardServerParts(
        server=server,
        html=html,
        handler_cls=handler_cls,
        bound_host=str(bound_host),
        bound_port=int(bound_port),
    )
