import json
import sqlite3
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.history_schema import initialize_history_schema
from meshdash.history_store_chat import load_chat_page
from meshdash.http_routes_get import handle_dashboard_get


def _make_store(conn: sqlite3.Connection) -> SimpleNamespace:
    return SimpleNamespace(
        _conn=conn,
        _read_conn=None,
        _lock=threading.Lock(),
    )


def _insert_chat(conn: sqlite3.Connection, created_unix: int, message: dict[str, object]) -> int:
    cur = conn.execute(
        "INSERT INTO chat(created_unix, message_json) VALUES(?, ?)",
        (created_unix, json.dumps(message)),
    )
    return int(cur.lastrowid)


def test_load_chat_page_returns_older_rows_with_history_cursor() -> None:
    conn = sqlite3.connect(":memory:")
    initialize_history_schema(conn)
    _insert_chat(conn, 100, {"from": "!aaaa0001", "to": "^all", "text": "old"})
    second_id = _insert_chat(conn, 110, {"from": "!aaaa0002", "to": "^all", "text": "middle"})
    _insert_chat(conn, 120, {"from": "!aaaa0003", "to": "^all", "text": "new"})
    conn.commit()

    rows = load_chat_page(_make_store(conn), limit=5, before_id=second_id + 1, scope="all")

    assert [row["text"] for row in rows] == ["old", "middle"]
    assert rows[0]["_history_id"] == 1
    assert rows[0]["_history_created_unix"] == 100


def test_load_chat_page_filters_direct_peer_threads() -> None:
    conn = sqlite3.connect(":memory:")
    initialize_history_schema(conn)
    _insert_chat(conn, 100, {"from": "!local001", "to": "!peer0001", "scope": "direct", "text": "to peer"})
    _insert_chat(conn, 110, {"from": "!peer0001", "to": "!local001", "scope": "direct", "text": "from peer"})
    _insert_chat(conn, 120, {"from": "!other001", "to": "!local001", "scope": "direct", "text": "other"})
    _insert_chat(conn, 130, {"from": "!peer0001", "to": "^all", "text": "public"})
    conn.commit()

    rows = load_chat_page(_make_store(conn), limit=10, scope="direct", peer_id="!peer0001")

    assert [row["text"] for row in rows] == ["to peer", "from peer"]


def test_chat_history_route_uses_attached_state_loader() -> None:
    calls: list[dict[str, object]] = []

    def state_fn() -> dict[str, object]:
        return {}

    def chat_history_fn(**kwargs) -> list[dict[str, object]]:
        calls.append(kwargs)
        return [{"text": "older", "_history_id": 9, "_history_created_unix": 123}]

    setattr(state_fn, "chat_history_fn", chat_history_fn)
    written: list[tuple[int, dict[str, object], bool]] = []
    deps = SimpleNamespace(
        state_fn=state_fn,
        private_mode=False,
        to_int_fn=lambda raw: int(raw) if str(raw or "").strip() else None,
        write_json_response_fn=lambda _handler, *, status_code, payload_obj, no_store=False, **_kwargs: written.append(
            (status_code, payload_obj, no_store)
        ),
    )

    handle_dashboard_get(
        object(),
        path="/api/history/chat",
        query="limit=25&before_id=44&scope=direct&peer_id=!peer0001",
        deps=deps,
    )

    assert calls == [
        {
            "limit": 25,
            "before_id": 44,
            "before_unix": None,
            "scope": "direct",
            "peer_id": "!peer0001",
        }
    ]
    assert written[0][0] == 200
    assert written[0][1]["ok"] is True
    assert written[0][1]["messages"][0]["text"] == "older"
    assert written[0][1]["cursor"] == {"oldest_id": 9, "oldest_unix": 123}
    assert written[0][2] is True


def test_chat_history_route_blocks_private_mode() -> None:
    written: list[tuple[int, dict[str, object], bool]] = []
    deps = SimpleNamespace(
        state_fn=lambda: {},
        private_mode=True,
        api_metrics=None,
        write_json_response_fn=lambda _handler, *, status_code, payload_obj, no_store=False, **_kwargs: written.append(
            (status_code, payload_obj, no_store)
        ),
    )

    handle_dashboard_get(
        object(),
        path="/api/history/chat",
        query="",
        deps=deps,
    )

    assert written == [
        (
            403,
            {"ok": False, "error": "Chat history is disabled in private mode"},
            True,
        )
    ]
