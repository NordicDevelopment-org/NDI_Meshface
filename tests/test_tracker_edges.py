from meshdash.tracker_edges import is_direct_link, record_direct_edge_observation


def test_is_direct_link_filters_broadcast_unknown_and_self():
    assert is_direct_link("!a", "!b") is True
    assert is_direct_link("!a", "^all") is False
    assert is_direct_link("Unknown", "!b") is False
    assert is_direct_link("!a", "Unknown") is False
    assert is_direct_link("!a", "!a") is False


def test_record_direct_edge_observation_updates_session_and_historical():
    session_edges = {}
    historical_edges = {}

    key = record_direct_edge_observation(
        session_edges=session_edges,
        historical_edges=historical_edges,
        from_id="!a",
        to_id="!b",
        rx_time=100,
        portnum="NODEINFO_APP",
        hops=2,
        include_live_count=True,
    )
    assert key == ("!a", "!b")
    key = record_direct_edge_observation(
        session_edges=session_edges,
        historical_edges=historical_edges,
        from_id="!a",
        to_id="!b",
        rx_time=120,
        portnum="TEXT_MESSAGE_APP",
        hops=3,
        include_live_count=True,
    )
    assert key == ("!a", "!b")

    session = session_edges[("!a", "!b")]
    hist = historical_edges[("!a", "!b")]

    assert session["count"] == 2
    assert session["first_rx_time"] == 100
    assert session["last_rx_time"] == 120
    assert session["last_hops"] == 3
    assert session["hops_sum"] == 5
    assert session["hops_count"] == 2
    assert session["portnums"] == {"NODEINFO_APP", "TEXT_MESSAGE_APP"}

    assert hist["count"] == 2
    assert hist["first_rx_time"] == 100
    assert hist["last_rx_time"] == 120
    assert hist["last_hops"] == 3
    assert hist["hops_sum"] == 5
    assert hist["hops_count"] == 2
    assert hist["portnums"] == {"NODEINFO_APP", "TEXT_MESSAGE_APP"}


def test_record_direct_edge_observation_noop_for_non_direct():
    session_edges = {}
    historical_edges = {}
    key = record_direct_edge_observation(
        session_edges=session_edges,
        historical_edges=historical_edges,
        from_id="!a",
        to_id="^all",
        rx_time=100,
        portnum="TEXT_MESSAGE_APP",
        hops=1,
        include_live_count=True,
    )
    assert key is None
    assert session_edges == {}
    assert historical_edges == {}
