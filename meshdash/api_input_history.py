from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qs

from .runtime_types import ToIntFn

@dataclass(frozen=True)
class NodeHistoryQuery:
    node_id: str
    hours_override: Optional[int]
    points_override: Optional[int]


@dataclass(frozen=True)
class OnlineActivityQuery:
    hours_override: Optional[int]


def parse_node_history_request(
    raw_query: str,
    *,
    to_int_fn: ToIntFn,
) -> NodeHistoryQuery:
    query = parse_qs(raw_query)
    return NodeHistoryQuery(
        node_id=(query.get("node_id", [""])[0] or "").strip(),
        hours_override=to_int_fn(query.get("hours", [""])[0]),
        points_override=to_int_fn(query.get("points", [""])[0]),
    )


def parse_online_activity_request(
    raw_query: str,
    *,
    to_int_fn: ToIntFn,
) -> OnlineActivityQuery:
    query = parse_qs(raw_query)
    return OnlineActivityQuery(hours_override=to_int_fn(query.get("hours", [""])[0]))


def parse_node_history_query(
    raw_query: str,
    *,
    to_int_fn: ToIntFn,
) -> tuple[str, Optional[int], Optional[int]]:
    request = parse_node_history_request(raw_query, to_int_fn=to_int_fn)
    return request.node_id, request.hours_override, request.points_override


def parse_online_activity_query(
    raw_query: str,
    *,
    to_int_fn: ToIntFn,
) -> Optional[int]:
    request = parse_online_activity_request(raw_query, to_int_fn=to_int_fn)
    return request.hours_override
