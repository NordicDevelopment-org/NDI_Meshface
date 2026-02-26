import meshdash.tracker_runtime_receive_bindings as tracker_runtime_receive_bindings
from meshdash.tracker_runtime_receive_bindings import (
    _resolve_tracker_node_id_from_num,
    record_tracker_receive_unlocked_for_tracker,
)


def test_record_tracker_receive_unlocked_for_tracker_binds_node_resolver():
    observed = {}

    def _record_tracker_receive_unlocked(tracker, **kwargs):
        observed["tracker"] = tracker
        observed["kwargs"] = kwargs

    def _resolve_tracker_node_id_from_num_fn(
        iface, node_num, *, get_node_id_from_num_fn, **_kwargs
    ):
        observed["resolve_args"] = (iface, node_num, get_node_id_from_num_fn)
        return "!resolved"

    tracker = object()
    packet = {"id": 7}
    interface = object()
    sentinel_get_node_id = object()
    sentinel_record = object()
    sentinel_record_with_deps = object()

    record_tracker_receive_unlocked_for_tracker(
        tracker,
        packet=packet,
        interface=interface,
        include_live_count=False,
        get_node_id_from_num_fn=sentinel_get_node_id,
        record_tracker_packet_unlocked_fn=sentinel_record,
        record_tracker_packet_unlocked_with_dependencies_fn=sentinel_record_with_deps,
        resolve_tracker_node_id_from_num_fn=_resolve_tracker_node_id_from_num_fn,
        record_tracker_receive_unlocked_fn=_record_tracker_receive_unlocked,
    )

    assert observed["tracker"] is tracker
    assert observed["kwargs"]["packet"] == packet
    assert observed["kwargs"]["interface"] is interface
    assert observed["kwargs"]["include_live_count"] is False
    assert observed["kwargs"]["record_tracker_packet_unlocked_fn"] is sentinel_record
    assert (
        observed["kwargs"]["record_tracker_packet_unlocked_with_dependencies_fn"]
        is sentinel_record_with_deps
    )

    bound_resolver = observed["kwargs"]["get_node_id_from_num_fn"]
    assert bound_resolver("iface-x", 12345) == "!resolved"
    assert observed["resolve_args"] == ("iface-x", 12345, sentinel_get_node_id)


def test_resolve_tracker_node_id_from_num_forwards_dependencies(monkeypatch):
    observed = {}

    def _get_tracker_node_id_from_num(
        iface, node_num, *, meshtastic_module, to_int_fn, get_node_id_from_num_fn
    ):
        observed["args"] = (iface, node_num)
        observed["kwargs"] = {
            "meshtastic_module": meshtastic_module,
            "to_int_fn": to_int_fn,
            "get_node_id_from_num_fn": get_node_id_from_num_fn,
        }
        return "!abcd1234"

    monkeypatch.setattr(
        tracker_runtime_receive_bindings,
        "_get_tracker_node_id_from_num_helper",
        _get_tracker_node_id_from_num,
    )

    sentinel_meshtastic = object()
    sentinel_to_int = object()
    sentinel_get_node_id = object()

    result = _resolve_tracker_node_id_from_num(
        "iface-y",
        6789,
        meshtastic_module=sentinel_meshtastic,
        to_int_fn=sentinel_to_int,
        get_node_id_from_num_fn=sentinel_get_node_id,
    )

    assert result == "!abcd1234"
    assert observed["args"] == ("iface-y", 6789)
    assert observed["kwargs"] == {
        "meshtastic_module": sentinel_meshtastic,
        "to_int_fn": sentinel_to_int,
        "get_node_id_from_num_fn": sentinel_get_node_id,
    }


def test_resolve_tracker_node_id_from_num_returns_none_on_resolver_failure(monkeypatch):
    def _raise_get_tracker_node_id_from_num(
        iface, node_num, *, meshtastic_module, to_int_fn, get_node_id_from_num_fn
    ):
        raise RuntimeError("resolver boom")

    monkeypatch.setattr(
        tracker_runtime_receive_bindings,
        "_get_tracker_node_id_from_num_helper",
        _raise_get_tracker_node_id_from_num,
    )

    assert (
        _resolve_tracker_node_id_from_num(
            "iface-z",
            123,
            meshtastic_module=object(),
            to_int_fn=object(),
            get_node_id_from_num_fn=object(),
        )
        is None
    )
