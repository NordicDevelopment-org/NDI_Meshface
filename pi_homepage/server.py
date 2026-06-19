import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

from health import TileHealthMonitor

ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def _read_asset(name: str) -> str:
    return (ASSETS_DIR / name).read_text(encoding="utf-8")


def _escape_html(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_tile_card(tile: dict) -> str:
    tile_id = _escape_html(tile.get("id", ""))
    name = _escape_html(tile.get("name", tile_id))
    icon = _escape_html(tile.get("icon", "*"))
    url = _escape_html(tile.get("url", "#"))
    return (
        f'<a class="homepage-tile" data-tile-id="{tile_id}" href="{url}" target="_blank" rel="noopener">'
        f'<div class="homepage-tile-icon">{icon}</div>'
        f'<div class="homepage-tile-name">{name}</div>'
        f'<div class="homepage-tile-url">{url}</div>'
        '<div class="homepage-tile-status-row">'
        '<span class="homepage-tile-status-dot" data-status="unknown"></span>'
        '<span class="homepage-tile-status-label">unknown</span>'
        "</div>"
        "</a>"
    )


def render_homepage_html(
    *,
    app_title: str,
    tiles: list,
    theme_css: str,
    refresh_ms: int,
    initial_theme: str = "light",
) -> str:
    html_tmpl = _read_asset("homepage.html.tmpl")
    css_tmpl = _read_asset("homepage.css.tmpl")
    tile_cards = "\n".join(render_tile_card(tile) for tile in tiles)
    refresh_seconds = max(1, int(refresh_ms / 1000))
    replacements = {
        "{{APP_TITLE}}": _escape_html(app_title),
        "{{INITIAL_THEME}}": initial_theme,
        "{{THEME_CSS}}": theme_css,
        "{{HOMEPAGE_CSS}}": css_tmpl,
        "{{TILE_CARDS}}": tile_cards,
        "{{REFRESH_SECONDS}}": str(refresh_seconds),
        "{{REFRESH_MS}}": str(int(refresh_ms)),
    }
    html = html_tmpl
    for token, value in replacements.items():
        html = html.replace(token, value)
    return html


def build_homepage_handler_class(
    *,
    html_provider: Callable[[], str],
    health_monitor: TileHealthMonitor,
) -> type[BaseHTTPRequestHandler]:
    class HomepageHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _write_response(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            try:
                if self.path in ("/", "/index.html"):
                    self._write_response(200, "text/html; charset=utf-8", html_provider().encode("utf-8"))
                    return
                if self.path == "/api/status":
                    payload = json.dumps(
                        {"tiles": health_monitor.snapshot(), "generated_at": time.time()}
                    ).encode("utf-8")
                    self._write_response(200, "application/json", payload)
                    return
                self._write_response(404, "text/plain; charset=utf-8", b"not found")
            except (BrokenPipeError, ConnectionResetError):
                return

        def do_HEAD(self) -> None:
            try:
                self.send_response(200 if self.path in ("/", "/index.html") else 404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
            except (BrokenPipeError, ConnectionResetError):
                return

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002 (matches BaseHTTPRequestHandler signature)
            return

    return HomepageHandler


def build_homepage_server(
    *,
    host: str,
    port: int,
    html_provider: Callable[[], str],
    health_monitor: TileHealthMonitor,
) -> ThreadingHTTPServer:
    handler_cls = build_homepage_handler_class(html_provider=html_provider, health_monitor=health_monitor)
    return ThreadingHTTPServer((host, port), handler_cls)
