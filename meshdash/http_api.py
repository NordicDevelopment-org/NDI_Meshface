import json
from http.server import BaseHTTPRequestHandler
from typing import Any, Callable, Optional
from urllib.parse import parse_qs, urlparse

from .helpers import to_int


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
                    body = html_text.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return

                if path == "/api/state":
                    payload = json.dumps(state_fn(), separators=(",", ":")).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                if path == "/api/history/node":
                    query = parse_qs(parsed.query)
                    node_id = (query.get("node_id", [""])[0] or "").strip()
                    hours_override = to_int_fn(query.get("hours", [""])[0])
                    points_override = to_int_fn(query.get("points", [""])[0])
                    if node_history_fn is None:
                        response_obj = {"node_id": node_id, "points": [], "positions": [], "summary": {}}
                    else:
                        response_obj = node_history_fn(node_id, hours_override, points_override)
                    payload = json.dumps(response_obj, separators=(",", ":")).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                if path == "/api/history/online":
                    query = parse_qs(parsed.query)
                    hours_override = to_int_fn(query.get("hours", [""])[0])
                    if online_activity_fn is None:
                        clean_hours = (
                            hours_override
                            if isinstance(hours_override, int) and hours_override > 0
                            else default_node_history_hours
                        )
                        response_obj = {
                            "window_hours": clean_hours,
                            "timezone": "local",
                            "timezone_label": "local",
                            "points": [],
                            "hourly_profile": [
                                {
                                    "hour": hour,
                                    "label": f"{hour:02d}:00",
                                    "avg_online_nodes": None,
                                    "sample_hours": 0,
                                    "peak_online_nodes": 0,
                                }
                                for hour in range(24)
                            ],
                            "summary": {
                                "sample_hours": 0,
                                "distinct_nodes": 0,
                                "max_online_nodes": 0,
                                "avg_online_nodes": None,
                                "best_hour": None,
                                "best_hour_label": None,
                                "best_hour_avg_online_nodes": None,
                                "window_start": None,
                                "window_end": None,
                            },
                        }
                    else:
                        response_obj = online_activity_fn(hours_override)
                    payload = json.dumps(response_obj, separators=(",", ":")).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                self.send_response(404)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Not Found")
            except (BrokenPipeError, ConnectionResetError):
                return

        def do_POST(self) -> None:
            try:
                parsed = urlparse(self.path)
                path = parsed.path
                if path != "/api/chat/send":
                    self.send_response(404)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(b'{"ok":false,"error":"Not Found"}')
                    return

                if send_chat_fn is None:
                    payload = json.dumps(
                        {"ok": False, "error": "Chat send is not enabled on this dashboard instance"},
                        separators=(",", ":"),
                    ).encode("utf-8")
                    self.send_response(503)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                content_length = to_int_fn(self.headers.get("Content-Length")) or 0
                if content_length <= 0 or content_length > 8192:
                    payload = json.dumps(
                        {"ok": False, "error": "Invalid request size"},
                        separators=(",", ":"),
                    ).encode("utf-8")
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                raw = self.rfile.read(content_length)
                try:
                    body = json.loads(raw.decode("utf-8"))
                except Exception:
                    body = {}

                text = body.get("text") if isinstance(body, dict) else None
                destination = body.get("destination") if isinstance(body, dict) else None
                channel_index = to_int_fn(body.get("channel_index")) if isinstance(body, dict) else None
                reply_id = to_int_fn(body.get("reply_id")) if isinstance(body, dict) else None
                retry_of = to_int_fn(body.get("retry_of")) if isinstance(body, dict) else None
                emoji = body.get("emoji") if isinstance(body, dict) else None

                try:
                    response_obj = send_chat_fn(
                        text=text,
                        destination=destination,
                        channel_index=channel_index,
                        reply_id=reply_id,
                        retry_of=retry_of,
                        emoji=emoji,
                    )
                except ValueError as exc:
                    payload = json.dumps(
                        {"ok": False, "error": str(exc)},
                        separators=(",", ":"),
                    ).encode("utf-8")
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return
                except Exception as exc:
                    payload = json.dumps(
                        {"ok": False, "error": f"Send failed: {exc}"},
                        separators=(",", ":"),
                    ).encode("utf-8")
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                payload = json.dumps(response_obj, separators=(",", ":")).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                return

        def log_message(self, format: str, *args: Any) -> None:
            return

    return DashboardHandler
