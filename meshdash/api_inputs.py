import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional
from urllib.parse import parse_qs

def parse_online_activity_query(
    raw_query: str,
    *,
    to_int_fn: Callable[[Any], Optional[int]],
) -> Optional[int]:
    query = parse_qs(raw_query)
    return to_int_fn(query.get("hours", [""])[0])


def validate_content_length(
    headers: Mapping[str, Any],
    *,
    to_int_fn: Callable[[Any], Optional[int]],
    max_bytes: int = 8192,
) -> int:
    content_length = to_int_fn(headers.get("Content-Length")) or 0
    if content_length <= 0 or content_length > max_bytes:
        raise ValueError("Invalid request size")
    return content_length


@dataclass(frozen=True)
class ChatSendRequest:
    text: Any
    destination: Any
    channel_index: Optional[int]
    reply_id: Optional[int]
    retry_of: Optional[int]
    emoji: Any


@dataclass(frozen=True)
class NodeHistoryQuery:
    node_id: str
    hours_override: Optional[int]
    points_override: Optional[int]


def parse_node_history_request(
    raw_query: str,
    *,
    to_int_fn: Callable[[Any], Optional[int]],
) -> NodeHistoryQuery:
    query = parse_qs(raw_query)
    return NodeHistoryQuery(
        node_id=(query.get("node_id", [""])[0] or "").strip(),
        hours_override=to_int_fn(query.get("hours", [""])[0]),
        points_override=to_int_fn(query.get("points", [""])[0]),
    )


def parse_chat_send_request(
    raw_body: bytes,
    *,
    to_int_fn: Callable[[Any], Optional[int]],
) -> ChatSendRequest:
    try:
        body = json.loads(raw_body.decode("utf-8"))
    except Exception:
        body = {}
    payload = body if isinstance(body, dict) else {}
    return ChatSendRequest(
        text=payload.get("text"),
        destination=payload.get("destination"),
        channel_index=to_int_fn(payload.get("channel_index")),
        reply_id=to_int_fn(payload.get("reply_id")),
        retry_of=to_int_fn(payload.get("retry_of")),
        emoji=payload.get("emoji"),
    )


def parse_chat_send_body(
    raw_body: bytes,
    *,
    to_int_fn: Callable[[Any], Optional[int]],
) -> dict:
    request = parse_chat_send_request(raw_body, to_int_fn=to_int_fn)
    return {
        "text": request.text,
        "destination": request.destination,
        "channel_index": request.channel_index,
        "reply_id": request.reply_id,
        "retry_of": request.retry_of,
        "emoji": request.emoji,
    }


def parse_node_history_query(
    raw_query: str,
    *,
    to_int_fn: Callable[[Any], Optional[int]],
) -> tuple[str, Optional[int], Optional[int]]:
    request = parse_node_history_request(raw_query, to_int_fn=to_int_fn)
    return request.node_id, request.hours_override, request.points_override
