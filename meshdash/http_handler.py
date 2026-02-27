from http.server import BaseHTTPRequestHandler
from typing import Callable

from .http_handler_contracts import DashboardHttpHandler


def build_dashboard_handler_class(
    *,
    dispatch_get_fn: Callable[[DashboardHttpHandler], None],
    dispatch_post_fn: Callable[[DashboardHttpHandler], None],
) -> type[BaseHTTPRequestHandler]:
    class DashboardHandler(BaseHTTPRequestHandler):
        # BaseHTTPRequestHandler defaults to HTTP/1.0 which disables keep-alive.
        # The dashboard polls frequently; HTTP/1.1 persistent connections cut
        # latency and CPU by avoiding a new TCP handshake per request.
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:
            try:
                dispatch_get_fn(self)
            except (BrokenPipeError, ConnectionResetError):
                return

        def do_POST(self) -> None:
            try:
                dispatch_post_fn(self)
            except (BrokenPipeError, ConnectionResetError):
                return

        def log_message(self, format: str, *args: object) -> None:
            return

    return DashboardHandler
