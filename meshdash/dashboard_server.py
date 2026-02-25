from dataclasses import dataclass
from typing import Any, Callable

from .revision import RevisionInfo


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
    state_fn: Callable[[], dict],
    node_history_fn: Callable[..., dict],
    online_activity_fn: Callable[..., dict],
    send_chat_fn: Callable[..., dict],
    render_html_fn: Callable[..., str],
    make_http_handler_fn: Callable[..., Any],
    threading_http_server_cls: Any,
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
