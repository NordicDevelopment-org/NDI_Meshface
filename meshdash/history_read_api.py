from typing import Any, Callable, Dict, List


def load_recent_packets_data(
    conn: Any,
    *,
    limit: int,
    fetch_recent_packet_rows_fn: Callable[..., Any],
    decode_recent_packets_rows_fn: Callable[[Any], List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    rows = fetch_recent_packet_rows_fn(conn, limit=limit)
    return decode_recent_packets_rows_fn(rows)


def load_recent_chat_data(
    conn: Any,
    *,
    limit: int,
    fetch_recent_chat_rows_fn: Callable[..., Any],
    decode_recent_chat_rows_fn: Callable[[Any], List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    rows = fetch_recent_chat_rows_fn(conn, limit=limit)
    return decode_recent_chat_rows_fn(rows)


def load_connections_data(
    conn: Any,
    *,
    fetch_connection_rows_fn: Callable[..., Any],
    decode_connections_rows_fn: Callable[[Any], List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    rows = fetch_connection_rows_fn(conn)
    return decode_connections_rows_fn(rows)


def load_node_saved_counts_data(
    conn: Any,
    *,
    fetch_node_saved_count_rows_fn: Callable[..., Any],
    decode_node_saved_counts_rows_fn: Callable[[Any], Dict[str, Dict[str, Any]]],
) -> Dict[str, Dict[str, Any]]:
    rows = fetch_node_saved_count_rows_fn(conn)
    return decode_node_saved_counts_rows_fn(rows)


def load_node_capabilities_data(
    conn: Any,
    *,
    fetch_node_capability_rows_fn: Callable[..., Any],
    decode_node_capabilities_rows_fn: Callable[[Any], Dict[str, Dict[str, Any]]],
) -> Dict[str, Dict[str, Any]]:
    rows = fetch_node_capability_rows_fn(conn)
    return decode_node_capabilities_rows_fn(rows)
