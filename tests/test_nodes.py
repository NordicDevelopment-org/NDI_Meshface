from datetime import datetime, timezone

from meshdash.nodes import (
    extract_position,
    get_local_node_id,
    get_local_node_num,
    get_node_id_from_num,
    parse_utc_text_to_unix,
    safe_nodes_items,
    utc_now,
)


class _IfaceWithNodes:
    def __init__(self, nodes_by_num, my_info=None, local_node=None):
        self.nodesByNum = nodes_by_num
        self.myInfo = my_info
        self.localNode = local_node


class _FlakyNodesIface:
    def __init__(self):
        self._calls = 0
        self._nodes = {1: {"user": {"id": "!00000001"}}}

    @property
    def nodesByNum(self):
        self._calls += 1
        if self._calls == 1:
            raise RuntimeError("temporary read error")
        return self._nodes


class _AlwaysFailNodesIface:
    @property
    def nodesByNum(self):
        raise RuntimeError("always failing")


def test_utc_helpers_round_trip_epoch():
    stamp = utc_now()
    parsed = parse_utc_text_to_unix(stamp)
    assert parsed is not None
    assert datetime.fromtimestamp(parsed, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ") == stamp
    assert parse_utc_text_to_unix("invalid") is None


def test_get_node_id_from_num_handles_broadcast_and_fallback_hex():
    iface = _IfaceWithNodes({17: {"user": {"id": "!custom17"}}})
    assert get_node_id_from_num(iface, 4294967295, broadcast_num=4294967295) == "^all"
    assert get_node_id_from_num(iface, 17, broadcast_num=4294967295) == "!custom17"
    assert get_node_id_from_num(iface, 31, broadcast_num=4294967295) == "!0000001f"
    assert get_node_id_from_num(iface, "bad", broadcast_num=4294967295) is None


def test_get_local_node_num_prefers_my_info_then_local_node():
    iface_from_my_info = _IfaceWithNodes({}, my_info={"myNodeNum": 123})
    assert get_local_node_num(iface_from_my_info) == 123

    class _LocalNode:
        nodeNum = 456

    iface_from_local = _IfaceWithNodes({}, my_info={}, local_node=_LocalNode())
    assert get_local_node_num(iface_from_local) == 456


def test_get_local_node_id_uses_node_lookup_or_local_literal():
    iface = _IfaceWithNodes(
        {456: {"user": {"id": "!local456"}}},
        my_info={"my_node_num": 456},
    )
    assert get_local_node_id(iface, broadcast_num=4294967295) == "!local456"

    missing = _IfaceWithNodes({}, my_info={})
    assert get_local_node_id(missing, broadcast_num=4294967295) == "local"


def test_extract_position_returns_lat_lon_tuple():
    node_info = {"position": {"latitude": 44.98, "longitude": -93.26}}
    assert extract_position(node_info) == (44.98, -93.26)


def test_safe_nodes_items_handles_transient_and_hard_failure():
    flaky = _FlakyNodesIface()
    assert safe_nodes_items(flaky, retries=3, sleep_seconds=0.0) == [(1, {"user": {"id": "!00000001"}})]

    always_fail = _AlwaysFailNodesIface()
    assert safe_nodes_items(always_fail, retries=2, sleep_seconds=0.0) == []
