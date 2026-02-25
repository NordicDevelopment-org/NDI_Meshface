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
class DashboardServerDependencies:
    args: Any
    revision_info: RevisionInfo
    history_enabled: bool
    state_fn: StateFn
    node_history_fn: NodeHistoryFn
    online_activity_fn: OnlineActivityFn
    send_chat_fn: SendChatFn
    render_html_fn: RenderHtmlFn
    make_http_handler_fn: MakeHttpHandlerFn
    threading_http_server_cls: ThreadingHttpServerCls
