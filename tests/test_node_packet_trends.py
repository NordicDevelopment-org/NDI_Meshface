import sqlite3
import threading
import time
from types import SimpleNamespace

from meshdash.history_node_packet_trends import load_node_packet_trends
from meshdash.history_schema import initialize_history_schema


def _make_store(conn: sqlite3.Connection) -> SimpleNamespace:
    return SimpleNamespace(
        _conn=conn,
        _read_conn=None,
        _read_lock=None,
        _lock=threading.Lock(),
    )


def _insert_packet_event(
    conn: sqlite3.Connection,
    *,
    created_unix: int,
    from_id: str | None,
    to_id: str | None,
    portnum: str = "TEXT_MESSAGE_APP",
) -> None:
    conn.execute(
        """
        INSERT INTO packet_events(created_unix, from_id, to_id, portnum)
        VALUES(?, ?, ?, ?)
        """,
        (created_unix, from_id, to_id, portnum),
    )


def test_load_node_packet_trends_builds_all_node_rx_tx_history() -> None:
    conn = sqlite3.connect(":memory:")
    initialize_history_schema(conn)
    now = int(time.time())
    _insert_packet_event(conn, created_unix=now - 50, from_id="!self", to_id="!peer")
    _insert_packet_event(conn, created_unix=now - 400, from_id="!peer", to_id="!self")
    _insert_packet_event(conn, created_unix=now - 10, from_id="!self", to_id="!self")
    _insert_packet_event(conn, created_unix=now - 10, from_id="!admin", to_id="!self", portnum="ADMIN_APP")
    _insert_packet_event(conn, created_unix=now - 10, from_id="!local", to_id="^local")
    conn.commit()

    payload = load_node_packet_trends(
        _make_store(conn),
        local_node_id="!self",
        window_seconds=3600,
        bucket_count=24,
        recent_window_seconds=300,
    )

    nodes = payload["nodes"]
    assert set(nodes) == {"!peer", "!self"}
    assert nodes["!self"]["txTotal"] == 1
    assert nodes["!self"]["rxTotal"] == 1
    assert nodes["!self"]["txRecent5m"] == 1
    assert nodes["!self"]["rxRecent5m"] == 0
    assert sum(nodes["!self"]["buckets"]) == 2
    assert nodes["!peer"]["txTotal"] == 1
    assert nodes["!peer"]["rxTotal"] == 1
    assert sum(nodes["!peer"]["buckets"]) == 2
