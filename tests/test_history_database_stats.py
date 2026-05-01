import json
import sqlite3
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.history_schema import initialize_history_schema
from meshdash.history_store_database_stats import load_database_stats
from meshdash.http_routes_get import handle_dashboard_get


def _make_store(conn: sqlite3.Connection, db_path: str) -> SimpleNamespace:
    return SimpleNamespace(
        _conn=conn,
        _read_conn=None,
        _lock=threading.Lock(),
        db_path=db_path,
        max_rows=250,
        retention_seconds=7 * 86400,
        event_max_rows=1000,
        event_retention_seconds=3 * 86400,
        rollup_retention_seconds=30 * 86400,
    )


def test_history_database_stats_counts_tables_and_policy(tmp_path: Path) -> None:
    db_path = tmp_path / "history.db"
    conn = sqlite3.connect(db_path)
    initialize_history_schema(conn)
    conn.executemany(
        "INSERT INTO packets(created_unix, summary_json, packet_json) VALUES(?, ?, ?)",
        [
            (100, json.dumps({"portnum": "TEXT_MESSAGE_APP"}), json.dumps({"id": 1})),
            (200, json.dumps({"portnum": "NODEINFO_APP"}), json.dumps({"id": 2})),
        ],
    )
    conn.execute(
        """
        INSERT INTO packet_events(created_unix, from_id, to_id, portnum)
        VALUES(?, ?, ?, ?)
        """,
        (150, "!11111111", "^all", "TEXT_MESSAGE_APP"),
    )
    conn.execute(
        "INSERT INTO chat(created_unix, message_json) VALUES(?, ?)",
        (175, json.dumps({"text": "hello"})),
    )
    conn.commit()

    stats = load_database_stats(_make_store(conn, str(db_path)))

    assert stats["ok"] is True
    assert stats["enabled"] is True
    assert stats["path"] == str(db_path)
    assert stats["size_bytes"] > 0
    assert stats["total_size_bytes"] >= stats["size_bytes"]
    assert stats["table_counts"]["packets"] == 2
    assert stats["table_counts"]["packet_events"] == 1
    assert stats["table_counts"]["chat"] == 1
    assert stats["total_rows"] >= 4
    assert stats["ranges"]["packets"] == {"first_unix": 100, "last_unix": 200}
    assert stats["page_count"] > 0
    assert stats["page_size"] > 0
    assert stats["policy"]["retention_days"] == 7
    assert stats["policy"]["event_retention_days"] == 3
    assert stats["policy"]["rollup_retention_days"] == 30


def test_database_stats_route_uses_attached_state_helper() -> None:
    def state_fn() -> dict[str, object]:
        return {}

    setattr(state_fn, "database_stats_fn", lambda: {"ok": True, "enabled": True, "total_rows": 7})
    written: list[tuple[int, dict[str, object], bool]] = []
    deps = SimpleNamespace(
        state_fn=state_fn,
        write_json_response_fn=lambda _handler, *, status_code, payload_obj, no_store=False, **_kwargs: written.append(
            (status_code, payload_obj, no_store)
        ),
    )

    handle_dashboard_get(
        object(),
        path="/api/system/database",
        query="",
        deps=deps,
    )

    assert written == [(200, {"ok": True, "enabled": True, "total_rows": 7}, True)]


def test_database_stats_route_reports_unavailable_without_helper() -> None:
    written: list[tuple[int, dict[str, object], bool]] = []
    deps = SimpleNamespace(
        state_fn=lambda: {},
        write_json_response_fn=lambda _handler, *, status_code, payload_obj, no_store=False, **_kwargs: written.append(
            (status_code, payload_obj, no_store)
        ),
    )

    handle_dashboard_get(
        object(),
        path="/api/system/database",
        query="",
        deps=deps,
    )

    assert written == [
        (
            200,
            {
                "ok": False,
                "enabled": False,
                "error": "history database unavailable on this dashboard instance",
            },
            True,
        )
    ]
