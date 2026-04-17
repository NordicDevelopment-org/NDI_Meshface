import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.tracker_ingest import parse_tracker_packet
from meshdash.tracker_observation import apply_tracker_observation
from meshdash.tracker_storage import apply_tracker_storage_updates


def _node_id_from_num(_interface: object, node_num: object) -> str:
    mapping = {
        101: "!00000065",
        202: "!000000ca",
        303: "!0000012f",
    }
    try:
        clean = int(node_num)
    except (TypeError, ValueError):
        return ""
    return mapping.get(clean, "")


def test_parse_tracker_packet_extracts_neighbor_info_edges() -> None:
    packet = {
        "from": 101,
        "to": 4294967295,
        "rxTime": 1234,
        "decoded": {
            "portnum": "NEIGHBORINFO_APP",
            "neighborinfo": {
                "node_id": 101,
                "neighbors": [
                    {"node_id": 202, "snr": 8.5, "last_rx_time": 1200},
                    {"node_id": 303, "snr": 4.25, "last_rx_time": 1210},
                ],
            },
        },
    }

    parsed = parse_tracker_packet(
        packet,
        object(),
        get_node_id_from_num_fn=_node_id_from_num,
        to_int_fn=lambda value: int(value) if value is not None else None,
        calculate_hops_fn=lambda _start, _limit: None,
        extract_packet_position_fn=lambda _packet: None,
        extract_packet_battery_level_fn=lambda _packet: None,
        extract_reply_id_fn=lambda _decoded: None,
        extract_emoji_codepoint_fn=lambda _decoded: None,
        emoji_from_codepoint_fn=lambda _codepoint: "",
    )

    assert parsed["neighbor_info_edges"] == [
        {"from_id": "!00000065", "to_id": "!000000ca", "rx_time": 1200, "rx_snr": 8.5},
        {"from_id": "!00000065", "to_id": "!0000012f", "rx_time": 1210, "rx_snr": 4.25},
    ]


def test_apply_tracker_observation_records_neighbor_info_edges() -> None:
    parsed = {
        "decoded": {"portnum": "NEIGHBORINFO_APP"},
        "from_id": "!00000065",
        "to_id": "^all",
        "rx_time": 1234,
        "hops": None,
        "portnum": "NEIGHBORINFO_APP",
        "rx_snr": 2.0,
        "rx_rssi": -90,
        "neighbor_info_edges": [
            {"from_id": "!00000065", "to_id": "!000000ca", "rx_time": 1200, "rx_snr": 8.5},
            {"from_id": "!00000065", "to_id": "!0000012f", "rx_time": 1210, "rx_snr": 4.25},
        ],
    }
    session_edges: dict[tuple[str, str], dict[str, object]] = {}
    historical_edges: dict[tuple[str, str], dict[str, object]] = {}
    port_counts: dict[str, int] = {}

    direct_keys = apply_tracker_observation(
        parsed=parsed,
        include_live_count=True,
        session_edges=session_edges,
        historical_edges=historical_edges,
        port_counts=port_counts,
        apply_routing_delivery_update_fn=lambda *_args, **_kwargs: None,
        extract_update_fn=lambda _decoded: None,
        set_delivery_state_fn=lambda *_args, **_kwargs: None,
        record_direct_edge_observation_fn=__import__("meshdash.tracker_edges", fromlist=["record_direct_edge_observation"]).record_direct_edge_observation,
    )

    assert direct_keys == (("!00000065", "!000000ca"), ("!00000065", "!0000012f"))
    assert session_edges[("!00000065", "!000000ca")]["snr_sum"] == 8.5
    assert session_edges[("!00000065", "!0000012f")]["snr_sum"] == 4.25
    assert port_counts["NEIGHBORINFO_APP"] == 1


def test_apply_tracker_storage_updates_persists_multiple_connection_edges() -> None:
    class _HistoryStore:
        def __init__(self) -> None:
            self.saved: list[tuple[str, str, object, object, object]] = []
            self.packets: list[dict[str, object]] = []

        def save_connection_event(self, *, from_id: str, to_id: str, rx_time: object, portnum: object, hops: object) -> None:
            self.saved.append((from_id, to_id, rx_time, portnum, hops))

        def save_packet(self, packet_entry: dict[str, object]) -> None:
            self.packets.append(packet_entry)

        def save_chat(self, chat_entry: dict[str, object]) -> None:
            raise AssertionError("chat should not be saved for neighbor info")

    history = _HistoryStore()
    recent_packets: list[dict[str, object]] = []
    recent_chat: list[dict[str, object]] = []

    apply_tracker_storage_updates(
        recent_packets=recent_packets,
        recent_chat=recent_chat,
        history_store=history,
        include_live_count=True,
        direct_keys=(("!00000065", "!000000ca"), ("!00000065", "!0000012f")),
        rx_time=1234,
        portnum="NEIGHBORINFO_APP",
        hops=0,
        packet_entry={"summary": {"portnum": "NEIGHBORINFO_APP"}},
        chat_entry=None,
    )

    assert history.saved == [
        ("!00000065", "!000000ca", 1234, "NEIGHBORINFO_APP", 0),
        ("!00000065", "!0000012f", 1234, "NEIGHBORINFO_APP", 0),
    ]
    assert len(recent_packets) == 1
