import threading

import meshdash.history_store_nodes as history_store_nodes_module
from meshdash.history_store import HistoryStore
from meshdash.history_store_chat import (
    load_recent_chat as load_recent_chat_domain,
    save_chat as save_chat_domain,
)
from meshdash.history_store_connections import (
    load_connections as load_connections_domain,
    save_connection_event as save_connection_event_domain,
)
from meshdash.history_store_nodes import (
    load_node_capabilities as load_node_capabilities_domain,
    load_node_history as load_node_history_domain,
    load_online_activity as load_online_activity_domain,
    load_node_saved_counts as load_node_saved_counts_domain,
)
from meshdash.history_store_packets import (
    load_recent_packets as load_recent_packets_domain,
    save_packet as save_packet_domain,
)
from meshdash.history_store_reads import (
    load_connections,
    load_recent_chat,
)
from meshdash.history_store_writes import (
    save_chat,
    save_connection_event,
)


def _make_store(tmp_path):
    db_path = tmp_path / "history_wrappers.sqlite3"
    return HistoryStore(
        db_path=str(db_path),
        max_rows=5000,
        retention_days=7,
        event_max_rows=200000,
        event_retention_days=30,
        rollup_retention_days=365,
    )


def test_history_store_write_and_read_wrappers_round_trip_chat(tmp_path):
    store = _make_store(tmp_path)
    try:
        save_chat(
            store,
            {
                "from": "!a",
                "to": "!b",
                "text": "hello",
                "rx_time": "2026-02-24 00:00:00Z",
            },
        )
        recent_chat = load_recent_chat(store, 10)
        assert recent_chat
        assert recent_chat[-1]["text"] == "hello"
    finally:
        store.close()


def test_history_store_write_and_read_wrappers_round_trip_connections(tmp_path):
    store = _make_store(tmp_path)
    try:
        save_connection_event(
            store,
            from_id="!a",
            to_id="!b",
            rx_time=1_700_000_000,
            portnum="TEXT_MESSAGE_APP",
            hops=2,
        )
        rows = load_connections(store)
        assert rows
        assert rows[0]["from"] == "!a"
        assert rows[0]["to"] == "!b"
        assert rows[0]["count"] >= 1
    finally:
        store.close()


def test_history_store_domain_modules_round_trip_packet_chat_and_connection(tmp_path):
    store = _make_store(tmp_path)
    try:
        save_packet_domain(
            store,
            {
                "summary": {
                    "from": "!p1",
                    "to": "!p2",
                    "rx_time_unix": 1_700_000_100,
                    "rx_snr": 1.5,
                    "rx_rssi": -110.0,
                    "hops": 1,
                    "portnum": "TEXT_MESSAGE_APP",
                    "text": "packet text",
                },
                "packet": {
                    "id": 1_700_000_100,
                    "fromId": "!p1",
                    "toId": "!p2",
                    "rxTime": 1_700_000_100,
                },
            },
        )
        packets = load_recent_packets_domain(store, 10)
        assert packets
        assert packets[-1]["summary"]["from"] == "!p1"

        save_chat_domain(
            store,
            {
                "from": "!c1",
                "to": "!c2",
                "text": "chat text",
                "rx_time": "2026-02-24 00:00:00Z",
            },
        )
        chat_rows = load_recent_chat_domain(store, 10)
        assert chat_rows
        assert chat_rows[-1]["text"] == "chat text"

        save_connection_event_domain(
            store,
            from_id="!n1",
            to_id="!n2",
            rx_time=1_700_000_123,
            portnum="NODEINFO_APP",
            hops=3,
        )
        connection_rows = load_connections_domain(store)
        assert connection_rows
        assert connection_rows[0]["from"] == "!n1"
        assert connection_rows[0]["to"] == "!n2"
    finally:
        store.close()


def test_history_store_domain_node_modules_return_mapping_shapes(tmp_path):
    store = _make_store(tmp_path)
    try:
        capabilities = load_node_capabilities_domain(store)
        saved_counts = load_node_saved_counts_domain(store)
        assert isinstance(capabilities, dict)
        assert isinstance(saved_counts, dict)
    finally:
        store.close()


def test_history_store_domain_node_history_and_online_wrappers_delegate(monkeypatch):
    calls = {"node_history": None, "online_activity": None}

    def _fake_load_node_history_data(
        conn,
        *,
        node_id,
        window_hours,
        max_points,
        fetch_node_history_rows_fn,
        build_node_history_payload_fn,
        now_unix_fn,
    ):
        calls["node_history"] = {
            "conn": conn,
            "node_id": node_id,
            "window_hours": window_hours,
            "max_points": max_points,
            "fetch_fn": fetch_node_history_rows_fn,
            "build_fn": build_node_history_payload_fn,
            "now_unix": now_unix_fn(),
        }
        return {"ok": True, "kind": "node"}

    def _fake_load_online_activity_data(
        conn,
        *,
        window_hours,
        fetch_online_activity_rows_fn,
        build_online_activity_payload_fn,
        now_unix_fn,
    ):
        calls["online_activity"] = {
            "conn": conn,
            "window_hours": window_hours,
            "fetch_fn": fetch_online_activity_rows_fn,
            "build_fn": build_online_activity_payload_fn,
            "now_unix": now_unix_fn(),
        }
        return {"ok": True, "kind": "online"}

    monkeypatch.setattr(
        history_store_nodes_module,
        "_load_node_history_data_helper",
        _fake_load_node_history_data,
    )
    monkeypatch.setattr(
        history_store_nodes_module,
        "_load_online_activity_data_helper",
        _fake_load_online_activity_data,
    )

    class _Store:
        def __init__(self):
            self._conn = object()
            self._lock = threading.Lock()

    store = _Store()
    node_payload = load_node_history_domain(store, "!abc123", 24, 200)
    online_payload = load_online_activity_domain(store, 48)

    assert node_payload == {"ok": True, "kind": "node"}
    assert online_payload == {"ok": True, "kind": "online"}

    assert calls["node_history"]["conn"] is store._conn
    assert calls["node_history"]["node_id"] == "!abc123"
    assert calls["node_history"]["window_hours"] == 24
    assert calls["node_history"]["max_points"] == 200
    assert callable(calls["node_history"]["fetch_fn"])
    assert callable(calls["node_history"]["build_fn"])
    assert isinstance(calls["node_history"]["now_unix"], float)

    assert calls["online_activity"]["conn"] is store._conn
    assert calls["online_activity"]["window_hours"] == 48
    assert callable(calls["online_activity"]["fetch_fn"])
    assert callable(calls["online_activity"]["build_fn"])
    assert isinstance(calls["online_activity"]["now_unix"], float)
