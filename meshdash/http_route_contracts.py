from dataclasses import dataclass
from typing import Any, Callable, Optional

from .api_inputs import ChatSendRequest

StateFn = Callable[[], dict]
NodeHistoryFn = Callable[[str, Optional[int], Optional[int]], dict]
OnlineActivityFn = Callable[[Optional[int]], dict]
SendChatFn = Callable[..., dict]

ToIntFn = Callable[[Any], Optional[int]]
ParseNodeHistoryQueryFn = Callable[..., tuple[str, Optional[int], Optional[int]]]
ParseOnlineActivityQueryFn = Callable[..., Optional[int]]
EmptyNodeHistoryFn = Callable[[str], dict]
EmptyOnlineActivityFn = Callable[[int], dict]
ValidateContentLengthFn = Callable[..., int]
ParseChatSendRequestFn = Callable[..., ChatSendRequest]

WriteHtmlResponseFn = Callable[..., None]
WriteJsonResponseFn = Callable[..., None]
WriteTextResponseFn = Callable[..., None]


@dataclass(frozen=True)
class DashboardGetRouteDependencies:
    html_text: str
    state_fn: StateFn
    node_history_fn: Optional[NodeHistoryFn]
    online_activity_fn: Optional[OnlineActivityFn]
    default_node_history_hours: int
    to_int_fn: ToIntFn
    parse_node_history_query_fn: ParseNodeHistoryQueryFn
    parse_online_activity_query_fn: ParseOnlineActivityQueryFn
    empty_node_history_fn: EmptyNodeHistoryFn
    empty_online_activity_fn: EmptyOnlineActivityFn
    write_html_response_fn: WriteHtmlResponseFn
    write_json_response_fn: WriteJsonResponseFn
    write_text_response_fn: WriteTextResponseFn


@dataclass(frozen=True)
class DashboardPostRouteDependencies:
    send_chat_fn: Optional[SendChatFn]
    to_int_fn: ToIntFn
    validate_content_length_fn: ValidateContentLengthFn
    parse_chat_send_request_fn: ParseChatSendRequestFn
    write_json_response_fn: WriteJsonResponseFn
