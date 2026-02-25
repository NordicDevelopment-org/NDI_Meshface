from typing import Any, Callable, Optional

from .api_inputs import ChatSendRequest


def handle_chat_send_post(
    handler: Any,
    *,
    send_chat_fn: Optional[Callable[..., dict]],
    to_int_fn: Callable[[Any], Optional[int]],
    validate_content_length_fn: Callable[..., int],
    parse_chat_send_request_fn: Callable[..., ChatSendRequest],
    write_json_response_fn: Callable[..., None],
) -> None:
    if send_chat_fn is None:
        write_json_response_fn(
            handler,
            status_code=503,
            payload_obj={"ok": False, "error": "Chat send is not enabled on this dashboard instance"},
        )
        return

    try:
        content_length = validate_content_length_fn(
            handler.headers,
            to_int_fn=to_int_fn,
        )
    except ValueError:
        write_json_response_fn(
            handler,
            status_code=400,
            payload_obj={"ok": False, "error": "Invalid request size"},
        )
        return

    raw = handler.rfile.read(content_length)
    chat_request = parse_chat_send_request_fn(raw, to_int_fn=to_int_fn)

    try:
        response_obj = send_chat_fn(
            text=chat_request.text,
            destination=chat_request.destination,
            channel_index=chat_request.channel_index,
            reply_id=chat_request.reply_id,
            retry_of=chat_request.retry_of,
            emoji=chat_request.emoji,
        )
    except ValueError as exc:
        write_json_response_fn(
            handler,
            status_code=400,
            payload_obj={"ok": False, "error": str(exc)},
        )
        return
    except Exception as exc:
        write_json_response_fn(
            handler,
            status_code=500,
            payload_obj={"ok": False, "error": f"Send failed: {exc}"},
        )
        return

    write_json_response_fn(handler, status_code=200, payload_obj=response_obj, no_store=True)
