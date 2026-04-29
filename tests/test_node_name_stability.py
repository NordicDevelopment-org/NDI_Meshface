import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.helpers import to_int
from meshdash.history_backfill import backfill_node_capabilities
from meshdash.history_capabilities import decode_node_capabilities_rows
from meshdash.history_queries import fetch_node_capability_rows
from meshdash.history_schema import initialize_history_schema
from meshdash.history_writes import save_packet_event_and_rollups


def test_history_schema_backfills_node_first_seen_for_existing_capabilities() -> None:
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE node_capabilities (
          node_id TEXT PRIMARY KEY,
          last_seen_unix INTEGER NOT NULL,
          has_position INTEGER NOT NULL DEFAULT 0,
          last_position_unix INTEGER,
          last_hops INTEGER,
          battery_level INTEGER,
          battery_updated_unix INTEGER
        );
        CREATE TABLE node_metrics_1m (
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
        );
        CREATE TABLE node_positions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          created_unix INTEGER NOT NULL,
          node_id TEXT NOT NULL,
          lat REAL NOT NULL,
          lon REAL NOT NULL,
          altitude REAL,
          sats_in_view INTEGER
        );
        CREATE TABLE packet_events (
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
          channel INTEGER,
          want_ack INTEGER,
          priority TEXT,
          summary_json TEXT NOT NULL
        );
        INSERT INTO node_capabilities(node_id, last_seen_unix, has_position)
        VALUES('!a038f788', 1776515000, 0);
        INSERT INTO node_metrics_1m(
          bucket_unix, node_id, packet_count, snr_sum, snr_count, rssi_sum, rssi_count,
          hops_sum, hops_count, last_seen_unix
        )
        VALUES(1776514800, '!a038f788', 1, 0, 0, 0, 0, 0, 0, 1776514783);
        """
    )

    initialize_history_schema(conn)

    rows = fetch_node_capability_rows(conn)
    decoded = decode_node_capabilities_rows(rows)
    assert decoded["!a038f788"]["first_seen_unix"] == 1776514783


def test_save_packet_event_and_rollups_persists_latest_node_names_in_capabilities() -> None:
    conn = sqlite3.connect(":memory:")
    initialize_history_schema(conn)

    summary = {
        "from": "!a038f788",
        "to": "!08b3cb6d",
        "portnum": "NODEINFO_APP",
        "rx_time_unix": 1776514783,
        "hops": 2,
    }
    packet = {
        "fromId": "!a038f788",
        "toId": "!08b3cb6d",
        "rxTime": 1776514783,
        "decoded": {
            "portnum": "NODEINFO_APP",
            "user": {
                "id": "!a038f788",
                "longName": "NOT A HACKER",
                "shortName": "NAH",
            },
        },
    }

    save_packet_event_and_rollups(conn, summary, packet=packet, now_unix_fn=lambda: 1776514784.0)

    rows = fetch_node_capability_rows(conn)
    decoded = decode_node_capabilities_rows(rows)
    assert decoded["!a038f788"]["first_seen_unix"] == 1776514783
    assert decoded["!a038f788"]["last_long_name"] == "NOT A HACKER"
    assert decoded["!a038f788"]["last_short_name"] == "NAH"
    assert decoded["!a038f788"]["names_updated_unix"] == 1776514783


def test_backfill_node_capabilities_recovers_names_for_existing_history() -> None:
    conn = sqlite3.connect(":memory:")
    initialize_history_schema(conn)

    conn.execute(
        """
        INSERT INTO node_capabilities(
          node_id, last_seen_unix, has_position, last_position_unix,
          last_hops, battery_level, battery_updated_unix
        ) VALUES(?, ?, ?, ?, ?, ?, ?)
        """,
        ("!a038f788", 1776514000, 0, None, 2, None, None),
    )

    summary = {
        "captured_at": "2026-04-18 12:19:44Z",
        "from": "!a038f788",
        "to": "!08b3cb6d",
        "portnum": "NODEINFO_APP",
        "rx_time_unix": 1776514783,
    }
    packet = {
        "fromId": "!a038f788",
        "toId": "!08b3cb6d",
        "decoded": {
            "portnum": "NODEINFO_APP",
            "user": {
                "id": "!a038f788",
                "longName": "NOT A HACKER",
                "shortName": "NAH",
            },
        },
    }
    conn.execute(
        "INSERT INTO packets(created_unix, summary_json, packet_json) VALUES(?, ?, ?)",
        (1776514784, json.dumps(summary, separators=(",", ":")), json.dumps(packet, separators=(",", ":"))),
    )
    conn.commit()

    backfill_node_capabilities(conn, to_int_fn=to_int)

    rows = fetch_node_capability_rows(conn)
    decoded = decode_node_capabilities_rows(rows)
    assert decoded["!a038f788"]["first_seen_unix"] == 1776514000
    assert decoded["!a038f788"]["last_long_name"] == "NOT A HACKER"
    assert decoded["!a038f788"]["last_short_name"] == "NAH"
    assert decoded["!a038f788"]["names_updated_unix"] == 1776514784
