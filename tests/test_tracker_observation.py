from collections import Counter

from meshdash.tracker_observation import apply_tracker_observation


def test_apply_tracker_observation_updates_delivery_port_counts_and_direct_edge():
    observed = {}
    parsed = {
        "decoded": {"portnum": "TEXT_MESSAGE_APP"},
        "from_id": "!a",
        "to_id": "!b",
        "rx_time": 123,
        "hops": 2,
        "portnum": "TEXT_MESSAGE_APP",
    }
    port_counts = Counter()

    def _apply_delivery(decoded, *, extract_update_fn, set_delivery_state_fn):
        observed["decoded"] = decoded
        observed["extract"] = extract_update_fn
        observed["set"] = set_delivery_state_fn

    def _record_direct(**kwargs):
        observed["direct"] = kwargs
        return ("!a", "!b")

    extract_fn = object()
    set_fn = object()
    direct_key = apply_tracker_observation(
        parsed=parsed,
        include_live_count=True,
        session_edges={},
        historical_edges={},
        port_counts=port_counts,
        apply_routing_delivery_update_fn=_apply_delivery,
        extract_update_fn=extract_fn,
        set_delivery_state_fn=set_fn,
        record_direct_edge_observation_fn=_record_direct,
    )

    assert direct_key == ("!a", "!b")
    assert observed["decoded"] == {"portnum": "TEXT_MESSAGE_APP"}
    assert observed["extract"] is extract_fn
    assert observed["set"] is set_fn
    assert port_counts == Counter({"TEXT_MESSAGE_APP": 1})
    assert observed["direct"] == {
        "session_edges": {},
        "historical_edges": {},
        "from_id": "!a",
        "to_id": "!b",
        "rx_time": 123,
        "portnum": "TEXT_MESSAGE_APP",
        "hops": 2,
        "include_live_count": True,
    }


def test_apply_tracker_observation_skips_port_count_for_none_portnum():
    port_counts = Counter()
    parsed = {
        "decoded": {},
        "from_id": "!a",
        "to_id": "!b",
        "rx_time": 123,
        "hops": None,
        "portnum": None,
    }

    apply_tracker_observation(
        parsed=parsed,
        include_live_count=False,
        session_edges={},
        historical_edges={},
        port_counts=port_counts,
        apply_routing_delivery_update_fn=lambda *_args, **_kwargs: None,
        extract_update_fn=lambda _decoded: None,
        set_delivery_state_fn=lambda *_args, **_kwargs: None,
        record_direct_edge_observation_fn=lambda **_kwargs: ("!a", "!b"),
    )

    assert port_counts == Counter()
