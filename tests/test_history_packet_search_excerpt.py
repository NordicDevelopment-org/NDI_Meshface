import json
import sqlite3
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.history_schema import initialize_history_schema
from meshdash.history_store_packets import search_packets


def _build_store(conn: sqlite3.Connection) -> SimpleNamespace:
    return SimpleNamespace(
        _conn=conn,
        _read_conn=None,
        _lock=threading.Lock(),
    )


def test_search_packets_returns_visible_match_excerpt_for_packet_and_chat_rows() -> None:
    conn = sqlite3.connect(":memory:")
    initialize_history_schema(conn)
    store = _build_store(conn)

    packet_summary = {
        "packet_id": 101,
        "from": "!11111111",
        "to": "^all",
        "portnum": "TELEMETRY_APP",
    }
    packet_payload = {
        "id": 101,
        "decoded": {
            "telemetry": {
                "device_metrics": {
                    "note": "operator typed sudo reboot during maintenance",
                }
            }
        },
    }
    summary_match = {
        "packet_id": 102,
        "from": "!22222222",
        "to": "^all",
        "portnum": "TEXT_MESSAGE_APP",
        "text": "sudo appears in summary text",
    }
    chat_match = {
        "from": "!33333333",
        "to": "^all",
        "portnum": "TEXT_MESSAGE_APP",
        "text": "chat says sudo too",
        "message_id": 5001,
    }

    conn.execute(
        "INSERT INTO packets(created_unix, summary_json, packet_json) VALUES (?, ?, ?)",
        (100, json.dumps(packet_summary), json.dumps(packet_payload)),
    )
    conn.execute(
        "INSERT INTO packets(created_unix, summary_json, packet_json) VALUES (?, ?, ?)",
        (200, json.dumps(summary_match), json.dumps({"id": 102, "decoded": {"text": "plain"}})),
    )
    conn.execute(
        "INSERT INTO chat(created_unix, message_json) VALUES (?, ?)",
        (300, json.dumps(chat_match)),
    )
    conn.commit()

    payload = search_packets(
        store,
        "sudo",
        source="both",
        scope="both",
        limit=10,
    )

    assert payload["ok"] is True
    matches = [entry for entry in payload["entries"] if isinstance(entry, dict) and entry.get("match") is True]
    assert len(matches) == 3

    packet_hidden = next(
        entry for entry in matches
        if entry.get("source") == "packet" and entry.get("summary", {}).get("packet_id") == 101
    )
    assert packet_hidden["match_scope"] == "packet"
    assert "sudo reboot" in str(packet_hidden["match_excerpt"])

    packet_summary_hit = next(
        entry for entry in matches
        if entry.get("source") == "packet" and entry.get("summary", {}).get("packet_id") == 102
    )
    assert packet_summary_hit["match_scope"] == "summary"
    assert "sudo appears in summary text" in str(packet_summary_hit["match_excerpt"])

    chat_hit = next(entry for entry in matches if entry.get("source") == "chat")
    assert chat_hit["match_scope"] == "chat"
    assert "chat says sudo too" in str(chat_hit["match_excerpt"])
