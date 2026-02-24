from typing import Any, Callable, Optional

from .api_chat import (
    handle_chat_send_post as _handle_chat_send_post_helper,
)


def handle_dashboard_post(
    handler: Any,
    *,
    path: str,
    send_chat_fn: Optional[Callable[..., dict]],
    to_int_fn: Callable[[Any], Optional[int]],
    validate_content_length_fn: Callable[..., int],
    parse_chat_send_body_fn: Callable[..., dict],
    write_json_response_fn: Callable[..., None],
) -> None:
    if path != "/api/chat/send":
        write_json_response_fn(
            handler,
            status_code=404,
            payload_obj={"ok": False, "error": "Not Found"},
        )
        return

    _handle_chat_send_post_helper(
        handler,
        send_chat_fn=send_chat_fn,
        to_int_fn=to_int_fn,
        validate_content_length_fn=validate_content_length_fn,
        parse_chat_send_body_fn=parse_chat_send_body_fn,
        write_json_response_fn=write_json_response_fn,
    )
