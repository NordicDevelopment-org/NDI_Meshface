import types

from meshdash.state import build_state, collect_local_state, collect_nodes


class _DummyTracker:
    def snapshot(self, by_id):
        self.by_id = by_id
        return {
            "live_packet_count": 4,
            "real_edge_count": 2,
            "edges": [{"from": "!00000001", "to": "!00000002", "count": 1}],
            "port_counts": [{"portnum": "TEXT_MESSAGE_APP", "count": 3}],
            "recent_packets": [{"summary": {"packet_id": 1}, "packet": {"id": 1}}],
            "recent_chat": [{"text": "hello"}],
        }

    def load_node_saved_counts(self):
        return {
            "!00000002": {
                "saved_packets": 7,
                "saved_points": 3,
                "saved_last_seen": "2026-01-01 00:00:00Z",
            }
        }

    def load_node_capabilities(self):
        return {"!00000002": {"last_seen": "2026-01-01 00:00:00Z"}}


def _iface_with_local(local_node=None):
    if local_node is None:
        local_node = types.SimpleNamespace(
            localConfig={"lora": {"modem_preset": "LONG_FAST"}, "password": "secret"},
            moduleConfig={"foo": "bar"},
            channels=[{"name": "primary"}],
        )
    iface = types.SimpleNamespace(
        nodesByNum={
            2: {
                "num": 2,
                "user": {"id": "!00000002", "shortName": "B", "longName": "Bravo"},
                "deviceMetrics": {"batteryLevel": 88},
                "position": {"latitude": 44.98, "longitude": -93.26},
                "lastHeard": 200,
            },
            1: {
                "num": 1,
                "user": {"shortName": "A", "longName": "Alpha"},
                "deviceMetrics": {"batteryLevel": 77},
                "lastHeard": 100,
            },
        },
        myInfo={"password": "mysecret"},
        metadata={"board": "x1"},
        localNode=local_node,
    )
    iface.getNode = lambda _node_id: local_node
    return iface


def test_collect_nodes_builds_rows_and_counts_positions():
    nodes = collect_nodes(_iface_with_local())
    assert len(nodes["rows"]) == 2
    assert nodes["rows"][0]["id"] == "!00000002"
    assert nodes["rows"][1]["id"] == "!00000001"
    assert nodes["with_position_count"] == 1
    assert nodes["rows"][0]["lat"] == 44.98
    assert nodes["rows"][0]["lon"] == -93.26


def test_collect_local_state_falls_back_to_getnode_when_needed():
    local = types.SimpleNamespace(
        localConfig={"lora": {"modem_preset": "MEDIUM_FAST"}},
        moduleConfig={"foo": "bar"},
        channels=[{"name": "primary"}],
    )
    iface = _iface_with_local(local_node=None)
    iface.localNode = None
    iface.getNode = lambda _node_id: local
    state = collect_local_state(iface)
    assert state["local_config"]["lora"]["modem_preset"] == "MEDIUM_FAST"
    assert len(state["channels"]) == 1


def test_collect_local_state_includes_local_position_from_node_registry():
    local = types.SimpleNamespace(
        nodeNum=2,
        localConfig={"lora": {"modem_preset": "MEDIUM_FAST"}},
        moduleConfig={"foo": "bar"},
        channels=[{"name": "primary"}],
    )
    iface = _iface_with_local(local_node=local)
    iface.myInfo = {"my_node_num": 2}

    state = collect_local_state(iface)

    assert state["local_node_num"] == 2
    assert state["local_node_info"]["num"] == 2
    assert state["local_position"]["latitude"] == 44.98
    assert state["local_position"]["longitude"] == -93.26


def test_build_state_merges_saved_counts_and_redacts_secrets():
    iface = _iface_with_local()
    tracker = _DummyTracker()
    state = build_state(
        iface=iface,
        tracker=tracker,
        started_at=0.0,
        target="192.168.1.109:4403 (tcp)",
        show_secrets=False,
        storage_probe_path=".",
        revision_info={"version": "0.1.0", "commit": "abc123", "label": "Rev: v0.1.0 (abc123)"},
        sensitive_field_names={"password"},
    )

    assert state["summary"]["target"] == "192.168.1.109:4403 (tcp)"
    assert state["summary"]["modem_preset"] == "LONG_FAST"
    assert state["summary"]["node_count"] == 2
    assert state["summary"]["nodes_with_position"] == 1
    assert state["nodes"][0]["saved_packets"] == 7
    assert state["nodes"][0]["saved_points"] == 3
    assert state["nodes"][0]["saved_last_seen"] == "2026-01-01 00:00:00Z"
    assert state["history_caps"]["!00000002"]["last_seen"] == "2026-01-01 00:00:00Z"
    assert state["my_info"]["password"] == "<redacted>"
    assert state["local_state"]["local_config"]["password"] == "<redacted>"
