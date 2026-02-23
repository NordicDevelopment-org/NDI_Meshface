from collections import Counter, deque

from meshdash.tracker_receive import process_parsed_tracker_packet


def test_process_parsed_tracker_packet_routes_observation_artifacts_and_storage():
    observed = {}
    parsed = {"rx_time": 123, "hops": 2, "portnum": "TEXT_MESSAGE_APP"}
    packet = {"id": 7}

    def _observe(**kwargs):
        observed["observe_kwargs"] = kwargs
        return ("!a", "!b")

    def _artifacts(**kwargs):
        observed["artifacts_kwargs"] = kwargs
        return {"summary": {"id": 7}}, {"text": "hello"}

    def _storage(**kwargs):
        observed["storage_kwargs"] = kwargs

    recent_packets = deque(maxlen=4)
    recent_chat = deque(maxlen=4)
    process_parsed_tracker_packet(
        packet=packet,
        parsed=parsed,
        include_live_count=True,
        session_edges={},
        historical_edges={},
        port_counts=Counter(),
        apply_tracker_observation_fn=_observe,
        apply_routing_delivery_update_fn="delivery-fn",
        extract_update_fn="extract-fn",
        set_delivery_state_fn="set-fn",
        record_direct_edge_observation_fn="edge-fn",
        build_tracker_packet_artifacts_fn=_artifacts,
        build_packet_summary_fn="summary-fn",
        build_chat_entry_from_packet_fn="chat-fn",
        utc_now_fn="utc-fn",
        format_epoch_fn="format-fn",
        to_int_fn="to-int-fn",
        to_jsonable_fn="to-json-fn",
        apply_tracker_storage_updates_fn=_storage,
        recent_packets=recent_packets,
        recent_chat=recent_chat,
        history_store="history-store",
    )

    assert observed["observe_kwargs"]["parsed"] == parsed
    assert observed["observe_kwargs"]["include_live_count"] is True
    assert observed["observe_kwargs"]["apply_routing_delivery_update_fn"] == "delivery-fn"
    assert observed["observe_kwargs"]["extract_update_fn"] == "extract-fn"
    assert observed["observe_kwargs"]["set_delivery_state_fn"] == "set-fn"
    assert observed["observe_kwargs"]["record_direct_edge_observation_fn"] == "edge-fn"

    assert observed["artifacts_kwargs"]["packet"] == packet
    assert observed["artifacts_kwargs"]["parsed"] == parsed
    assert observed["artifacts_kwargs"]["build_packet_summary_fn"] == "summary-fn"
    assert observed["artifacts_kwargs"]["build_chat_entry_from_packet_fn"] == "chat-fn"

    assert observed["storage_kwargs"] == {
        "recent_packets": recent_packets,
        "recent_chat": recent_chat,
        "history_store": "history-store",
        "include_live_count": True,
        "direct_key": ("!a", "!b"),
        "rx_time": 123,
        "portnum": "TEXT_MESSAGE_APP",
        "hops": 2,
        "packet_entry": {"summary": {"id": 7}},
        "chat_entry": {"text": "hello"},
    }
