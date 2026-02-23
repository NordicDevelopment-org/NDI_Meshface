from meshdash.history_read_api import (
    load_connections_data,
    load_node_capabilities_data,
    load_node_saved_counts_data,
    load_recent_chat_data,
    load_recent_packets_data,
)


def test_load_recent_packets_data_fetches_and_decodes():
    result = load_recent_packets_data(
        conn="conn",
        limit=5,
        fetch_recent_packet_rows_fn=lambda conn, limit: [conn, limit],
        decode_recent_packets_rows_fn=lambda rows: [{"rows": rows}],
    )
    assert result == [{"rows": ["conn", 5]}]


def test_load_recent_chat_data_fetches_and_decodes():
    result = load_recent_chat_data(
        conn="conn",
        limit=7,
        fetch_recent_chat_rows_fn=lambda conn, limit: [conn, limit],
        decode_recent_chat_rows_fn=lambda rows: [{"rows": rows}],
    )
    assert result == [{"rows": ["conn", 7]}]


def test_load_connections_data_fetches_and_decodes():
    result = load_connections_data(
        conn="conn",
        fetch_connection_rows_fn=lambda conn: [conn],
        decode_connections_rows_fn=lambda rows: [{"rows": rows}],
    )
    assert result == [{"rows": ["conn"]}]


def test_load_node_saved_counts_data_fetches_and_decodes():
    result = load_node_saved_counts_data(
        conn="conn",
        fetch_node_saved_count_rows_fn=lambda conn: [conn],
        decode_node_saved_counts_rows_fn=lambda rows: {"rows": rows},
    )
    assert result == {"rows": ["conn"]}


def test_load_node_capabilities_data_fetches_and_decodes():
    result = load_node_capabilities_data(
        conn="conn",
        fetch_node_capability_rows_fn=lambda conn: [conn],
        decode_node_capabilities_rows_fn=lambda rows: {"rows": rows},
    )
    assert result == {"rows": ["conn"]}
