from meshdash.state_service import _slim_history_caps, _slim_recent_packets


def test_slim_recent_packets_drops_raw_packet_blob_but_keeps_ui_fields() -> None:
    recent_packets = [
        {
            "summary": {
                "packet_id": 123,
                "from": "!from",
                "to": "!to",
                "portnum": "ROUTING_APP",
            },
            "packet": {
                "id": 123,
                "from": 1,
                "to": 2,
                "fromId": "!from",
                "toId": "!to",
                "channel": 7,
                "encrypted": "abc",
                "raw": {
                    "huge": "drop-me",
                    "decoded": {
                        "payload": "drop-me-too",
                    },
                },
                "decoded": {
                    "portnum": "ROUTING_APP",
                    "payload": "keep-me",
                    "routing": {
                        "requestId": 456,
                    },
                },
            },
        }
    ]

    slimmed = _slim_recent_packets(recent_packets)

    assert len(slimmed) == 1
    packet = slimmed[0]["packet"]
    assert packet["encrypted"] == "abc"
    assert packet["decoded"]["payload"] == "keep-me"
    assert packet["decoded"]["routing"]["requestId"] == 456
    assert "raw" not in packet
    assert "from_num" not in slimmed[0]["summary"]


def test_slim_history_caps_keeps_only_relevant_nodes_and_fields() -> None:
    history_caps = {
        "!node-a": {
            "last_seen_unix": 10,
            "last_seen": "2026-04-15 00:00:10Z",
            "has_position": True,
            "last_position_unix": 8,
            "last_position_time": "2026-04-15 00:00:08Z",
            "last_hops": 2,
            "battery_level": 90,
            "battery_updated_unix": 9,
        },
        "!node-b": {
            "last_seen_unix": 20,
            "battery_level": 40,
        },
    }

    slimmed = _slim_history_caps(
        history_caps,
        nodes=[{"id": "!node-a"}],
        recent_chat=[],
        recent_packets=[],
        edges=[],
        local_node_id="!local",
    )

    assert set(slimmed) == {"!node-a"}
    assert slimmed["!node-a"]["battery_level"] == 90
    assert "battery_updated_unix" not in slimmed["!node-a"]


def test_slim_recent_packets_caps_lite_buffer_length() -> None:
    recent_packets = [
        {
            "summary": {"packet_id": idx, "from": f"!{idx}", "to": "^all"},
            "packet": {"id": idx},
        }
        for idx in range(150)
    ]

    slimmed = _slim_recent_packets(recent_packets)

    assert len(slimmed) == 120
    assert slimmed[0]["summary"]["packet_id"] == 0
    assert slimmed[-1]["summary"]["packet_id"] == 119
