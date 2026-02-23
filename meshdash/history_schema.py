from typing import Any


SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS packets (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      created_unix INTEGER NOT NULL,
      summary_json TEXT NOT NULL,
      packet_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chat (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      created_unix INTEGER NOT NULL,
      message_json TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS connections (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      from_id TEXT NOT NULL,
      to_id TEXT NOT NULL,
      first_seen_unix INTEGER NOT NULL,
      last_seen_unix INTEGER NOT NULL,
      seen_count INTEGER NOT NULL,
      portnums_json TEXT NOT NULL,
      last_hops INTEGER,
      hops_sum INTEGER NOT NULL DEFAULT 0,
      hops_count INTEGER NOT NULL DEFAULT 0,
      UNIQUE(from_id, to_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS packet_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      created_unix INTEGER NOT NULL,
      from_id TEXT,
      to_id TEXT,
      portnum TEXT,
      rx_snr REAL,
      rx_rssi REAL,
      hops INTEGER,
      hop_start INTEGER,
      hop_limit INTEGER,
      channel TEXT,
      want_ack INTEGER,
      priority TEXT,
      summary_json TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS node_positions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      created_unix INTEGER NOT NULL,
      node_id TEXT NOT NULL,
      lat REAL NOT NULL,
      lon REAL NOT NULL,
      altitude REAL,
      sats_in_view INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS node_capabilities (
      node_id TEXT PRIMARY KEY,
      last_seen_unix INTEGER NOT NULL,
      has_position INTEGER NOT NULL DEFAULT 0,
      last_position_unix INTEGER,
      last_hops INTEGER,
      battery_level INTEGER,
      battery_updated_unix INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS node_metrics_1m (
      bucket_unix INTEGER NOT NULL,
      node_id TEXT NOT NULL,
      packet_count INTEGER NOT NULL,
      snr_sum REAL NOT NULL,
      snr_count INTEGER NOT NULL,
      snr_min REAL,
      snr_max REAL,
      rssi_sum REAL NOT NULL,
      rssi_count INTEGER NOT NULL,
      rssi_min REAL,
      rssi_max REAL,
      hops_sum INTEGER NOT NULL,
      hops_count INTEGER NOT NULL,
      hops_min INTEGER,
      hops_max INTEGER,
      last_seen_unix INTEGER NOT NULL,
      PRIMARY KEY(bucket_unix, node_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS link_metrics_1m (
      bucket_unix INTEGER NOT NULL,
      from_id TEXT NOT NULL,
      to_id TEXT NOT NULL,
      packet_count INTEGER NOT NULL,
      snr_sum REAL NOT NULL,
      snr_count INTEGER NOT NULL,
      snr_min REAL,
      snr_max REAL,
      rssi_sum REAL NOT NULL,
      rssi_count INTEGER NOT NULL,
      rssi_min REAL,
      rssi_max REAL,
      hops_sum INTEGER NOT NULL,
      hops_count INTEGER NOT NULL,
      hops_min INTEGER,
      hops_max INTEGER,
      last_seen_unix INTEGER NOT NULL,
      PRIMARY KEY(bucket_unix, from_id, to_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_packets_created_unix ON packets(created_unix)",
    "CREATE INDEX IF NOT EXISTS idx_chat_created_unix ON chat(created_unix)",
    "CREATE INDEX IF NOT EXISTS idx_connections_last_seen_unix ON connections(last_seen_unix)",
    "CREATE INDEX IF NOT EXISTS idx_packet_events_created_unix ON packet_events(created_unix)",
    "CREATE INDEX IF NOT EXISTS idx_packet_events_from_id ON packet_events(from_id)",
    "CREATE INDEX IF NOT EXISTS idx_packet_events_to_id ON packet_events(to_id)",
    "CREATE INDEX IF NOT EXISTS idx_packet_events_portnum ON packet_events(portnum)",
    "CREATE INDEX IF NOT EXISTS idx_node_positions_created_unix ON node_positions(created_unix)",
    "CREATE INDEX IF NOT EXISTS idx_node_positions_node_id_created_unix ON node_positions(node_id, created_unix)",
    "CREATE INDEX IF NOT EXISTS idx_node_capabilities_last_seen_unix ON node_capabilities(last_seen_unix)",
    "CREATE INDEX IF NOT EXISTS idx_node_metrics_1m_last_seen_unix ON node_metrics_1m(last_seen_unix)",
    "CREATE INDEX IF NOT EXISTS idx_link_metrics_1m_last_seen_unix ON link_metrics_1m(last_seen_unix)",
]


def initialize_history_schema(conn: Any) -> None:
    for statement in SCHEMA_STATEMENTS:
        conn.execute(statement)
