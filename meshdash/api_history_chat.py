_DEFAULT_CHAT_HISTORY_LIMIT = 320
_MAX_CHAT_HISTORY_LIMIT = 500


def _clean_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except Exception:
        return None
    return parsed if parsed > 0 else None


def _chat_history_cursor(messages: list[dict[str, object]]) -> dict[str, object]:
    if not messages:
        return {
            "oldest_id": None,
            "oldest_unix": None,
        }
    oldest = messages[0] if isinstance(messages[0], dict) else {}
    return {
        "oldest_id": _clean_int(oldest.get("_history_id")),
        "oldest_unix": _clean_int(
            oldest.get("_history_created_unix")
            or oldest.get("rx_time_unix")
            or oldest.get("created_unix")
        ),
    }


def build_chat_history_response(
    *,
    query_obj: dict[str, list[str]],
    chat_history_fn,
    to_int_fn,
) -> dict[str, object]:
    if not callable(chat_history_fn):
        return {
            "ok": False,
            "enabled": False,
            "error": "chat history unavailable on this dashboard instance",
            "messages": [],
            "count": 0,
            "has_more": False,
        }

    raw_limit = to_int_fn(query_obj.get("limit", [""])[0])
    limit = max(
        1,
        min(
            _MAX_CHAT_HISTORY_LIMIT,
            int(raw_limit or _DEFAULT_CHAT_HISTORY_LIMIT),
        ),
    )
    before_id = to_int_fn(
        query_obj.get("before_id", [""])[0]
        or query_obj.get("id", [""])[0]
    )
    before_unix = to_int_fn(
        query_obj.get("before_unix", [""])[0]
        or query_obj.get("before", [""])[0]
    )
    scope = str(query_obj.get("scope", [""])[0] or "").strip().lower()
    peer_id = str(
        query_obj.get("peer_id", [""])[0]
        or query_obj.get("peer", [""])[0]
        or ""
    ).strip()

    messages = chat_history_fn(
        limit=limit,
        before_id=before_id,
        before_unix=before_unix,
        scope=scope or None,
        peer_id=peer_id or None,
    )
    if not isinstance(messages, list):
        messages = []

    return {
        "ok": True,
        "enabled": True,
        "messages": messages,
        "count": len(messages),
        "limit": limit,
        "has_more": len(messages) >= limit,
        "cursor": _chat_history_cursor(messages),
    }
