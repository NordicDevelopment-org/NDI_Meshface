from types import SimpleNamespace

from meshdash.tracker_runtime_init import initialize_dashboard_tracker_runtime


def test_initialize_dashboard_tracker_runtime_wires_state_callbacks_and_bootstrap():
    tracker = SimpleNamespace()
    captured = {}

    buffers = SimpleNamespace(
        edges={"e": 1},
        historical_edges={"old": 2},
        port_counts={"TEXT": 3},
        recent_packets=["p1"],
        recent_chat=["c1"],
    )

    def _initialize_buffers(packet_limit):
        captured["packet_limit"] = packet_limit
        return buffers

    set_fn = object()
    extract_fn = object()
    expire_fn = object()

    def _build_callbacks(
        recent_chat,
        *,
        get_timeout_seconds_fn,
        to_int_fn,
        parse_utc_text_to_unix_fn,
        utc_now_fn,
        now_unix_fn,
    ):
        captured["callbacks_args"] = {
            "recent_chat": recent_chat,
            "get_timeout_seconds_fn": get_timeout_seconds_fn,
            "to_int_fn": to_int_fn,
            "parse_utc_text_to_unix_fn": parse_utc_text_to_unix_fn,
            "utc_now_fn": utc_now_fn,
            "now_unix_fn": now_unix_fn,
        }
        return {
            "set_delivery_state": set_fn,
            "extract_delivery_update": extract_fn,
            "expire_pending_deliveries": expire_fn,
        }

    historical_edges = {"new": 4}

    def _apply_bootstrap(
        *,
        history_store,
        packet_limit,
        recent_packets,
        recent_chat,
        load_tracker_history_bootstrap_fn,
        build_historical_edges_fn,
    ):
        captured["bootstrap_args"] = {
            "history_store": history_store,
            "packet_limit": packet_limit,
            "recent_packets": recent_packets,
            "recent_chat": recent_chat,
            "load_tracker_history_bootstrap_fn": load_tracker_history_bootstrap_fn,
            "build_historical_edges_fn": build_historical_edges_fn,
        }
        return historical_edges

    sentinel_history_store = object()
    sentinel_loader = object()
    sentinel_builder = object()
    sentinel_parse_utc = object()
    sentinel_utc_now = object()
    sentinel_to_int = object()
    sentinel_now_unix = object()

    initialize_dashboard_tracker_runtime(
        tracker,
        packet_limit=42,
        history_store=sentinel_history_store,
        default_chat_delivery_timeout_seconds=90,
        initialize_tracker_buffers_fn=_initialize_buffers,
        build_tracker_delivery_callbacks_fn=_build_callbacks,
        apply_tracker_history_bootstrap_fn=_apply_bootstrap,
        load_tracker_history_bootstrap_fn=sentinel_loader,
        build_historical_edges_fn=sentinel_builder,
        parse_utc_text_to_unix_fn=sentinel_parse_utc,
        utc_now_fn=sentinel_utc_now,
        to_int_fn=sentinel_to_int,
        now_unix_fn=sentinel_now_unix,
    )

    assert captured["packet_limit"] == 42
    assert tracker._history_store is sentinel_history_store
    assert tracker._chat_delivery_timeout_seconds == 90
    assert tracker.live_packet_count == 0
    assert tracker.edges == {"e": 1}
    assert tracker.port_counts == {"TEXT": 3}
    assert tracker.recent_packets == ["p1"]
    assert tracker.recent_chat == ["c1"]
    assert tracker._set_delivery_state_fn is set_fn
    assert tracker._extract_delivery_update_fn is extract_fn
    assert tracker._expire_pending_deliveries_fn is expire_fn
    assert tracker._historical_edges is historical_edges

    callbacks_args = captured["callbacks_args"]
    assert callbacks_args["recent_chat"] == ["c1"]
    assert callbacks_args["to_int_fn"] is sentinel_to_int
    assert callbacks_args["parse_utc_text_to_unix_fn"] is sentinel_parse_utc
    assert callbacks_args["utc_now_fn"] is sentinel_utc_now
    assert callbacks_args["now_unix_fn"] is sentinel_now_unix
    assert callbacks_args["get_timeout_seconds_fn"]() == 90
    tracker._chat_delivery_timeout_seconds = 5
    assert callbacks_args["get_timeout_seconds_fn"]() == 5

    assert captured["bootstrap_args"] == {
        "history_store": sentinel_history_store,
        "packet_limit": 42,
        "recent_packets": ["p1"],
        "recent_chat": ["c1"],
        "load_tracker_history_bootstrap_fn": sentinel_loader,
        "build_historical_edges_fn": sentinel_builder,
    }
