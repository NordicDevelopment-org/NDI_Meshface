import io
import json
import sqlite3
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.helpers import to_int
from meshdash.history_schema import initialize_history_schema
from meshdash.history_store_settings import load_bbs_settings, save_bbs_settings
from meshdash.html_js import build_dashboard_js
from meshdash.http_api import make_http_handler
from meshdash.http_api_get import build_get_route_dependencies
from meshdash.http_api_post import build_post_route_dependencies
from meshdash.http_routes_get import handle_dashboard_get
from meshdash.http_routes_post import handle_dashboard_post


class _FakeHandler:
    def __init__(self, body: bytes = b"", *, headers: dict[str, object] | None = None) -> None:
        self.path = "/"
        self.headers = headers or {}
        self.rfile = io.BytesIO(body)
        self.wfile = io.BytesIO()

    def send_response(self, code: int) -> None:
        self._last_code = code

    def send_header(self, key: str, value: str) -> None:
        pass

    def end_headers(self) -> None:
        pass


def _make_store(conn: sqlite3.Connection) -> SimpleNamespace:
    return SimpleNamespace(
        _conn=conn,
        _read_conn=None,
        _read_lock=None,
        _lock=threading.Lock(),
        _maybe_prune_unlocked=lambda: None,
    )


def test_bbs_settings_store_round_trips_normalized_values() -> None:
    conn = sqlite3.connect(":memory:")
    initialize_history_schema(conn)
    store = _make_store(conn)

    saved = save_bbs_settings(
        store,
        settings={
            "title": "  My   Packet Exchange  ",
            "board_id": " My Packet Exchange!!! ",
            "motd": "  hello   mesh   world  ",
        },
    )

    assert saved["ok"] is True
    assert saved["settings"] == {
        "title": "My Packet Exchange",
        "board_id": "my-packet-exchange",
        "motd": "hello mesh world",
    }

    loaded = load_bbs_settings(store)

    assert loaded["ok"] is True
    assert loaded["settings"] == saved["settings"]
    assert int(loaded["updated_unix"]) > 0


def test_handle_dashboard_get_dispatches_bbs_settings_route() -> None:
    handler = _FakeHandler()
    calls: list[tuple[int, object, bool]] = []

    deps = build_get_route_dependencies(
        html_text="<html></html>",
        state_fn=lambda: {},
        node_history_fn=None,
        online_activity_fn=None,
        default_node_history_hours=24,
        get_bbs_settings_fn=lambda: {
            "ok": True,
            "settings": {
                "title": "Packet Exchange",
                "board_id": "packet-exchange",
                "motd": "2400 baud online.",
            },
            "updated_unix": 123,
        },
        to_int_fn=to_int,
    )
    deps = type(deps)(
        **{
            **deps.__dict__,
            "write_json_response_fn": lambda handler, *, status_code, payload_obj, no_store=False, **kwargs: calls.append(
                (status_code, payload_obj, bool(no_store))
            ),
        }
    )

    handle_dashboard_get(handler, path="/api/settings/bbs", query="", deps=deps)

    assert calls == [
        (
            200,
            {
                "ok": True,
                "settings": {
                    "title": "Packet Exchange",
                    "board_id": "packet-exchange",
                    "motd": "2400 baud online.",
                },
                "updated_unix": 123,
            },
            True,
        )
    ]


def test_handle_dashboard_post_dispatches_bbs_settings_route() -> None:
    body = json.dumps(
        {
            "settings": {
                "title": "Node Space",
                "board_id": "node-space",
                "motd": "hello",
            }
        }
    ).encode("utf-8")
    handler = _FakeHandler(body, headers={"Content-Length": str(len(body))})
    calls: list[tuple[int, object, bool]] = []

    deps = build_post_route_dependencies(
        send_chat_fn=None,
        set_bbs_settings_fn=lambda request: {
            "ok": True,
            "settings": {
                "title": str(request.title),
                "board_id": str(request.board_id),
                "motd": str(request.motd),
            },
            "updated_unix": 456,
        },
        to_int_fn=to_int,
    )
    deps = type(deps)(
        **{
            **deps.__dict__,
            "write_json_response_fn": lambda handler, *, status_code, payload_obj, no_store=False, **kwargs: calls.append(
                (status_code, payload_obj, bool(no_store))
            ),
        }
    )

    handle_dashboard_post(handler, path="/api/settings/bbs", deps=deps)

    assert calls == [
        (
            200,
            {
                "ok": True,
                "settings": {
                    "title": "Node Space",
                    "board_id": "node-space",
                    "motd": "hello",
                },
                "updated_unix": 456,
            },
            True,
        )
    ]


def test_make_http_handler_passes_bbs_settings_hooks(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_get: dict[str, object] = {}
    captured_post: dict[str, object] = {}

    def _fake_build_get_route_dependencies(**kwargs):
        captured_get.update(kwargs)
        return object()

    def _fake_build_post_route_dependencies(**kwargs):
        captured_post.update(kwargs)
        return object()

    monkeypatch.setattr("meshdash.http_api.build_get_route_dependencies", _fake_build_get_route_dependencies)
    monkeypatch.setattr("meshdash.http_api.build_post_route_dependencies", _fake_build_post_route_dependencies)
    monkeypatch.setattr(
        "meshdash.http_api.build_dashboard_handler_class",
        lambda **kwargs: {"dispatch_get_fn": kwargs["dispatch_get_fn"], "dispatch_post_fn": kwargs["dispatch_post_fn"]},
    )

    def _state_fn():
        return {}

    def _get_bbs_settings_fn() -> dict[str, object]:
        return {"ok": True, "settings": {}}

    def _set_bbs_settings_fn(payload: object) -> dict[str, object]:
        return {"ok": True, "settings": payload}

    setattr(_state_fn, "get_bbs_settings_fn", _get_bbs_settings_fn)
    setattr(_state_fn, "set_bbs_settings_fn", _set_bbs_settings_fn)

    make_http_handler("<html></html>", _state_fn)

    assert captured_get["get_bbs_settings_fn"] is _get_bbs_settings_fn
    assert captured_post["set_bbs_settings_fn"] is _set_bbs_settings_fn


def test_dashboard_js_includes_bbs_settings_sync_flow() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
        bbs_enabled=True,
    )

    assert 'const bbsSettingsEndpoint = "/api/settings/bbs";' in js
    assert 'const bbsHostSettingsSaveDebounceMs = 360;' in js
    assert "async function fetchBbsHostSettings(options = null) {" in js
    assert "async function saveBbsHostSettings(options = null) {" in js
    assert 'body: JSON.stringify({ settings }),' in js
    assert 'queueBbsHostSettingsSave();' in js
    assert 'void fetchBbsHostSettings({ silent: true });' in js
