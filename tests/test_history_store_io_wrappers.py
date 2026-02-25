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
