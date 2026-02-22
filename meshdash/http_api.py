from http.server import BaseHTTPRequestHandler
from typing import Any, Callable, Optional
from urllib.parse import urlparse

from .api_inputs import (
    parse_chat_send_body,
    parse_node_history_query,
    parse_online_activity_query,
    validate_content_length,
)
from .helpers import to_int
from .http_responses import write_html_response, write_json_response, write_text_response
from .services import empty_node_history, empty_online_activity


def make_http_handler(
    html_text: str,
    state_fn: Callable[[], dict],
    node_history_fn: Optional[Callable[[str, Optional[int], Optional[int]], dict]] = None,
    online_activity_fn: Optional[Callable[[Optional[int]], dict]] = None,
    send_chat_fn: Optional[Callable[..., dict]] = None,
    default_node_history_hours: int = 72,
    to_int_fn: Callable[[Any], Optional[int]] = to_int,
):
    class DashboardHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            try:
                parsed = urlparse(self.path)
                path = parsed.path

                if path in ("/", "/index.html"):
                    write_html_response(self, html_text=html_text)
                    return

                if path == "/api/state":
                    write_json_response(self, status_code=200, payload_obj=state_fn(), no_store=True)
                    return

                if path == "/api/history/node":
                    node_id, hours_override, points_override = parse_node_history_query(
                        parsed.query,
                        to_int_fn=to_int_fn,
                    )
                    if node_history_fn is None:
                        response_obj = empty_node_history(node_id)
                    else:
                        response_obj = node_history_fn(node_id, hours_override, points_override)
                    write_json_response(self, status_code=200, payload_obj=response_obj, no_store=True)
                    return

                if path == "/api/history/online":
                    hours_override = parse_online_activity_query(
                        parsed.query,
                        to_int_fn=to_int_fn,
                    )
                    if online_activity_fn is None:
                        clean_hours = (
                            hours_override
                            if isinstance(hours_override, int) and hours_override > 0
                            else default_node_history_hours
                        )
                        response_obj = empty_online_activity(clean_hours)
                    else:
                        response_obj = online_activity_fn(hours_override)
                    write_json_response(self, status_code=200, payload_obj=response_obj, no_store=True)
                    return

                write_text_response(self, status_code=404, text="Not Found")
            except (BrokenPipeError, ConnectionResetError):
                return

        def do_POST(self) -> None:
            try:
                parsed = urlparse(self.path)
                path = parsed.path
                if path != "/api/chat/send":
                    write_json_response(
                        self,
                        status_code=404,
                        payload_obj={"ok": False, "error": "Not Found"},
                    )
                    return

                if send_chat_fn is None:
                    write_json_response(
                        self,
                        status_code=503,
                        payload_obj={"ok": False, "error": "Chat send is not enabled on this dashboard instance"},
                    )
                    return

                try:
                    content_length = validate_content_length(
                        self.headers,
                        to_int_fn=to_int_fn,
                    )
                except ValueError:
                    write_json_response(
                        self,
                        status_code=400,
                        payload_obj={"ok": False, "error": "Invalid request size"},
                    )
                    return

                raw = self.rfile.read(content_length)
                chat_request = parse_chat_send_body(raw, to_int_fn=to_int_fn)

                try:
                    response_obj = send_chat_fn(
                        text=chat_request["text"],
                        destination=chat_request["destination"],
                        channel_index=chat_request["channel_index"],
                        reply_id=chat_request["reply_id"],
                        retry_of=chat_request["retry_of"],
                        emoji=chat_request["emoji"],
                    )
                except ValueError as exc:
                    write_json_response(
                        self,
                        status_code=400,
                        payload_obj={"ok": False, "error": str(exc)},
                    )
                    return
                except Exception as exc:
                    write_json_response(
                        self,
                        status_code=500,
                        payload_obj={"ok": False, "error": f"Send failed: {exc}"},
                    )
                    return

                write_json_response(self, status_code=200, payload_obj=response_obj, no_store=True)
            except (BrokenPipeError, ConnectionResetError):
                return

        def log_message(self, format: str, *args: Any) -> None:
            return

    return DashboardHandler
