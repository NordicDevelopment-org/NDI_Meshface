from meshdash.tracker_history_edges import build_historical_edges


def test_build_historical_edges_normalizes_connection_rows():
    rows = [
        {
            "from": "!a",
            "to": "!b",
            "count": "3",
            "first_rx_time": 100,
            "last_rx_time": 150,
            "portnums": ["TEXT_MESSAGE_APP", "NODEINFO_APP"],
            "last_hops": 2,
            "hops_sum": "8",
            "hops_count": "4",
        }
    ]

    out = build_historical_edges(rows)
    edge = out[("!a", "!b")]
    assert edge["from"] == "!a"
    assert edge["to"] == "!b"
    assert edge["count"] == 3
    assert edge["first_rx_time"] == 100
    assert edge["last_rx_time"] == 150
    assert edge["portnums"] == {"TEXT_MESSAGE_APP", "NODEINFO_APP"}
    assert edge["last_hops"] == 2
    assert edge["hops_sum"] == 8
    assert edge["hops_count"] == 4


def test_build_historical_edges_handles_missing_optional_values():
    rows = [{"from": "!x", "to": "!y", "count": 1}]
    out = build_historical_edges(rows)
    edge = out[("!x", "!y")]
    assert edge["portnums"] == set()
    assert edge["hops_sum"] == 0
    assert edge["hops_count"] == 0
