from .http_handler_contracts import DashboardHttpHandler
from .http_route_contracts import (
    ManageZorkBotFn,
    ParseZorkBotToggleRequestFn,
    SetPingBotEnabledFn,
    SetPingBotMessageOnlyFn,
    SetZorkBotEnabledFn,
    ToIntFn,
    ValidateContentLengthFn,
    WriteJsonResponseFn,
)

_MAX_BOT_TOGGLE_POST_BYTES = 4096


def handle_zork_bot_toggle_post(
    handler: DashboardHttpHandler,
    *,
    set_zork_bot_enabled_fn: SetZorkBotEnabledFn | None,
    set_ping_bot_enabled_fn: SetPingBotEnabledFn | None,
    set_ping_bot_message_only_fn: SetPingBotMessageOnlyFn | None,
    manage_zork_bot_fn: ManageZorkBotFn | None,
    default_command: str = "zork",
    to_int_fn: ToIntFn,
    validate_content_length_fn: ValidateContentLengthFn,
    parse_zork_bot_toggle_request_fn: ParseZorkBotToggleRequestFn | None,
    write_json_response_fn: WriteJsonResponseFn,
) -> None:
    if parse_zork_bot_toggle_request_fn is None:
        write_json_response_fn(
            handler,
            status_code=503,
            payload_obj={"ok": False, "error": "Zork bot runtime is not enabled on this dashboard instance"},
        )
        return

    try:
        content_length = validate_content_length_fn(
            handler.headers,
            to_int_fn=to_int_fn,
            max_bytes=_MAX_BOT_TOGGLE_POST_BYTES,
        )
    except ValueError:
        write_json_response_fn(
            handler,
            status_code=400,
            payload_obj={"ok": False, "error": "Invalid request size"},
        )
        return

    raw = handler.rfile.read(content_length)
    try:
        request = parse_zork_bot_toggle_request_fn(raw)
    except ValueError as exc:
        write_json_response_fn(
            handler,
            status_code=400,
            payload_obj={"ok": False, "error": str(exc)},
        )
        return

    try:
        action = str(getattr(request, "action", "") or "").strip().lower().replace("-", "_")
        command = str(getattr(request, "command", "") or "").strip().lower().replace("-", "_")
        message_only = getattr(request, "message_only", None)
        if not command:
            command = str(default_command or "zork").strip().lower().replace("-", "_") or "zork"
        if command == "ping" and message_only is not None and action in {"", "set_mode", "configure"}:
            if set_ping_bot_message_only_fn is None:
                raise ValueError("Ping bot mode update is unavailable")
            response_obj = set_ping_bot_message_only_fn(bool(message_only))
        elif action in {"enable", "disable"}:
            enabled_flag = action == "enable"
            if command == "ping":
                if set_ping_bot_enabled_fn is None:
                    raise ValueError("Ping bot runtime toggle is unavailable")
                response_obj = set_ping_bot_enabled_fn(enabled_flag)
                if message_only is not None:
                    if set_ping_bot_message_only_fn is None:
                        raise ValueError("Ping bot mode update is unavailable")
                    response_obj = set_ping_bot_message_only_fn(bool(message_only))
            else:
                if set_zork_bot_enabled_fn is None:
                    raise ValueError("Zork bot runtime toggle is unavailable")
                response_obj = set_zork_bot_enabled_fn(enabled_flag)
        elif action in {"end_session", "clear_sessions"}:
            if command != "zork":
                raise ValueError("Session management is only available for zork")
            if manage_zork_bot_fn is None:
                raise ValueError("Zork bot session management is unavailable")
            response_obj = manage_zork_bot_fn(action, peer_id=getattr(request, "peer_id", None))
        else:
            raise ValueError("Unsupported Zork bot action")
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
            payload_obj={"ok": False, "error": f"Zork bot update failed: {exc}"},
        )
        return

    if not isinstance(response_obj, dict):
        response_obj = {"ok": bool(response_obj)}
    elif "ok" not in response_obj:
        response_obj = {**response_obj, "ok": True}
    status_code = 200 if bool(response_obj.get("ok")) else 400
    write_json_response_fn(handler, status_code=status_code, payload_obj=response_obj, no_store=True)


__all__ = ["handle_zork_bot_toggle_post"]
