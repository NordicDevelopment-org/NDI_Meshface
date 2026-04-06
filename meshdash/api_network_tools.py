from .http_handler_contracts import DashboardHttpHandler
from .http_route_contracts import (
    ParseNetworkToolRequestFn,
    RunNetworkToolFn,
    ToIntFn,
    ValidateContentLengthFn,
    WriteJsonResponseFn,
)


def handle_network_tool_post(
    handler: DashboardHttpHandler,
    *,
    run_network_tool_fn: RunNetworkToolFn | None,
    to_int_fn: ToIntFn,
    validate_content_length_fn: ValidateContentLengthFn,
    parse_network_tool_request_fn: ParseNetworkToolRequestFn | None,
    write_json_response_fn: WriteJsonResponseFn,
    max_bytes: int = 16384,
) -> None:
    if run_network_tool_fn is None or parse_network_tool_request_fn is None:
        write_json_response_fn(
            handler,
            status_code=503,
            payload_obj={"ok": False, "error": "Network tools are not enabled on this dashboard instance"},
        )
        return

    try:
        content_length = validate_content_length_fn(
            handler.headers,
            to_int_fn=to_int_fn,
            max_bytes=max_bytes,
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
        request = parse_network_tool_request_fn(raw, to_int_fn=to_int_fn)
    except ValueError as exc:
        write_json_response_fn(
            handler,
            status_code=400,
            payload_obj={"ok": False, "error": str(exc)},
        )
        return

    try:
        response_obj = run_network_tool_fn(request)
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
            payload_obj={"ok": False, "error": f"Network tool failed: {exc}"},
        )
        return

    status_code = 200 if bool(response_obj.get("ok")) else 400
    write_json_response_fn(
        handler,
        status_code=status_code,
        payload_obj=response_obj,
        no_store=True,
    )


__all__ = ["handle_network_tool_post"]
