from types import SimpleNamespace

from meshdash.tracker_node_resolver import get_tracker_node_id_from_num


def test_get_tracker_node_id_from_num_passes_meshtastic_broadcast_number():
    observed = {}

    def _resolver(iface, node_num, *, broadcast_num, to_int_fn):
        observed["iface"] = iface
        observed["node_num"] = node_num
        observed["broadcast_num"] = broadcast_num
        observed["to_int_fn"] = to_int_fn
        return "!abcd1234"

    sentinel_to_int = object()
    iface = object()
    result = get_tracker_node_id_from_num(
        iface,
        17,
        meshtastic_module=SimpleNamespace(BROADCAST_NUM=4242),
        to_int_fn=sentinel_to_int,
        get_node_id_from_num_fn=_resolver,
    )

    assert result == "!abcd1234"
    assert observed == {
        "iface": iface,
        "node_num": 17,
        "broadcast_num": 4242,
        "to_int_fn": sentinel_to_int,
    }


def test_get_tracker_node_id_from_num_uses_none_when_meshtastic_missing():
    observed = {}

    def _resolver(_iface, _node_num, *, broadcast_num, to_int_fn):
        observed["broadcast_num"] = broadcast_num
        observed["to_int_fn"] = to_int_fn
        return None

    sentinel_to_int = object()
    result = get_tracker_node_id_from_num(
        object(),
        99,
        meshtastic_module=None,
        to_int_fn=sentinel_to_int,
        get_node_id_from_num_fn=_resolver,
    )

    assert result is None
    assert observed == {
        "broadcast_num": None,
        "to_int_fn": sentinel_to_int,
    }
