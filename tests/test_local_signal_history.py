import sqlite3
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.history_schema import initialize_history_schema
from meshdash.history_store_nodes import load_node_history
from meshdash.html_js import build_dashboard_js


def test_load_node_history_uses_local_radio_signal_points_for_self_node() -> None:
    conn = sqlite3.connect(":memory:")
    initialize_history_schema(conn)
    now = int(time.time())
    bucket_a = now - 120
    bucket_b = now - 30
    conn.executemany(
        """
        INSERT INTO packet_events(
          created_unix, from_id, to_id, portnum,
          rx_snr, rx_rssi, hops, hop_start, hop_limit,
          channel, want_ack, priority, summary_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (bucket_a, "!11111111", "!abcd1234", "TEXT_MESSAGE_APP", 5.0, -100.0, 1, None, None, "0", 0, None, "{}"),
            (bucket_a + 10, "!22222222", "!abcd1234", "TEXT_MESSAGE_APP", 7.0, -90.0, 2, None, None, "0", 0, None, "{}"),
            (bucket_b, "!33333333", "!abcd1234", "TEXT_MESSAGE_APP", 10.0, -80.0, 1, None, None, "0", 0, None, "{}"),
        ],
    )
    conn.commit()

    store = SimpleNamespace(
        _conn=conn,
        _read_conn=None,
        _lock=threading.Lock(),
        local_node_id="!abcd1234",
    )

    history = load_node_history(store, "!abcd1234", 24, 240)

    assert history["points"] == []
    assert history["signal_source"] == "local-radio"
    signal_points = history["signal_points"]
    assert len(signal_points) == 2
    assert signal_points[0]["packet_count"] == 2
    assert signal_points[0]["avg_snr"] == 6.0
    assert signal_points[0]["avg_rssi"] == -95.0
    assert signal_points[1]["packet_count"] == 1
    assert signal_points[1]["avg_snr"] == 10.0
    assert signal_points[1]["avg_rssi"] == -80.0


def test_dashboard_js_uses_signal_points_when_available() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert "history.signal_points" in js
    assert "Signal plot uses packets heard by this radio." in js
