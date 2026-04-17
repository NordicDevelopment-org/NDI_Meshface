import sqlite3
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.history_schema import initialize_history_schema
from meshdash.history_store_summary import load_summary_metrics, save_summary_metrics


def _make_store(conn: sqlite3.Connection) -> SimpleNamespace:
    return SimpleNamespace(
        _conn=conn,
        _read_conn=None,
        _read_lock=None,
        _lock=threading.Lock(),
        _maybe_prune_unlocked=lambda: None,
    )


def test_summary_metrics_store_persists_edge_count_and_real_edge_count() -> None:
    conn = sqlite3.connect(":memory:")
    initialize_history_schema(conn)
    store = _make_store(conn)

    save_summary_metrics(
        store,
        {
            "node_count": 20,
            "saved_node_count": 18,
            "online_node_count": 9,
            "nodes_with_position": 6,
            "live_packet_count": 120,
            "edge_count": 77,
            "real_edge_count": 31,
        },
    )

    payload = load_summary_metrics(store, 1)
    points = payload.get("points") or []
    assert len(points) == 1
    point = points[0]
    assert point["edge_count"] == 77
    assert point["real_edge_count"] == 31
    assert payload["summary"]["latest"]["edge_count"] == 77
    assert payload["summary"]["latest"]["real_edge_count"] == 31


def test_history_schema_adds_edge_count_column_and_backfills_existing_rows() -> None:
    conn = sqlite3.connect(":memory:")
    now = int(time.time() // 60 * 60)
    conn.execute(
        """
        CREATE TABLE summary_metrics_1m (
          bucket_unix INTEGER PRIMARY KEY,
          node_count INTEGER NOT NULL DEFAULT 0,
          saved_node_count INTEGER NOT NULL DEFAULT 0,
          online_node_count INTEGER NOT NULL DEFAULT 0,
          nodes_with_position INTEGER NOT NULL DEFAULT 0,
          live_packet_count INTEGER NOT NULL DEFAULT 0,
          real_edge_count INTEGER NOT NULL DEFAULT 0,
          last_seen_unix INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO summary_metrics_1m(
          bucket_unix,
          node_count,
          saved_node_count,
          online_node_count,
          nodes_with_position,
          live_packet_count,
          real_edge_count,
          last_seen_unix
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (now, 10, 9, 4, 3, 50, 12, now),
    )
    conn.commit()

    initialize_history_schema(conn)

    columns = {
        str(row[1])
        for row in conn.execute('PRAGMA table_info("summary_metrics_1m")').fetchall()
    }
    assert "edge_count" in columns

    row = conn.execute(
        "SELECT edge_count, real_edge_count FROM summary_metrics_1m WHERE bucket_unix = ?",
        (now,),
    ).fetchone()
    assert row == (12, 12)

