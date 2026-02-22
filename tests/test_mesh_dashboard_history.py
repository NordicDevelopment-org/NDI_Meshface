import time
import types
from datetime import datetime

import mesh_dashboard as md
import pytest


def _packet_entry(from_id: str, rx_time_unix: int) -> dict:
    return {
        "summary": {
            "from": from_id,
            "to": "^all",
            "rx_time_unix": int(rx_time_unix),
            "rx_snr": 6.5,
            "rx_rssi": -98,
            "hops": 2,
            "portnum": "TEXT_MESSAGE_APP",
        },
        "packet": {
            "id": int(rx_time_unix),
            "fromId": from_id,
            "toId": "^all",
            "rxTime": int(rx_time_unix),
        },
    }


def _new_history_store(db_path: str) -> md.HistoryStore:
    return md.HistoryStore(
        db_path=db_path,
        max_rows=10000,
        retention_days=30,
        event_max_rows=20000,
        event_retention_days=30,
        rollup_retention_days=365,
    )


def test_load_online_activity_aggregates_distinct_nodes_per_hour(tmp_path):
    store = _new_history_store(str(tmp_path / "mesh_history.sqlite3"))
    try:
        now = int(time.time())
        anchor = now - (now % 3600)
        hot_hour = anchor - (2 * 3600)
        cool_hour = anchor - (1 * 3600)

        store.save_packet(_packet_entry("!node000a", hot_hour + 60))
        store.save_packet(_packet_entry("!node000a", hot_hour + 900))
        store.save_packet(_packet_entry("!node000b", hot_hour + 1200))
        store.save_packet(_packet_entry("!node000c", hot_hour + 1800))
        store.save_packet(_packet_entry("!node000a", cool_hour + 600))

        activity = store.load_online_activity(window_hours=4)
        assert activity["window_hours"] == 4
        assert activity["summary"]["sample_hours"] == 2
        assert activity["summary"]["distinct_nodes"] == 3
        assert activity["summary"]["max_online_nodes"] == 3
        assert activity["summary"]["avg_online_nodes"] == 2.0
        assert activity["summary"]["best_hour_label"] == datetime.fromtimestamp(hot_hour).strftime("%H:00")
        assert activity["summary"]["best_hour_avg_online_nodes"] == 3.0

        points = activity["points"]
        assert len(points) == 2
        assert points[0]["bucket_unix"] == hot_hour
        assert points[0]["online_nodes"] == 3
        assert points[1]["bucket_unix"] == cool_hour
        assert points[1]["online_nodes"] == 1
    finally:
        store.close()


def test_load_online_activity_returns_empty_shape_when_no_rollups(tmp_path):
    store = _new_history_store(str(tmp_path / "empty_mesh_history.sqlite3"))
    try:
        activity = store.load_online_activity(window_hours=12)
        assert activity["window_hours"] == 12
        assert activity["points"] == []
        assert len(activity["hourly_profile"]) == 24
        assert all(item["sample_hours"] == 0 for item in activity["hourly_profile"])
        assert activity["summary"]["sample_hours"] == 0
        assert activity["summary"]["distinct_nodes"] == 0
        assert activity["summary"]["max_online_nodes"] == 0
        assert activity["summary"]["best_hour"] is None
    finally:
        store.close()


def test_load_node_history_includes_saved_position_trail(tmp_path):
    store = _new_history_store(str(tmp_path / "position_mesh_history.sqlite3"))
    try:
        now = int(time.time())
        first = now - 600
        second = now - 120

        packet_one = _packet_entry("!node9001", first)
        packet_one["summary"]["portnum"] = "POSITION_APP"
        packet_one["summary"]["position"] = {
            "lat": 44.9701001,
            "lon": -93.2659002,
            "altitude": 312.0,
            "sats_in_view": 7,
        }
        packet_two = _packet_entry("!node9001", second)
        packet_two["summary"]["portnum"] = "POSITION_APP"
        packet_two["summary"]["position"] = {
            "lat": 44.9709001,
            "lon": -93.2645002,
            "altitude": 315.0,
            "sats_in_view": 8,
        }
        store.save_packet(packet_one)
        store.save_packet(packet_two)

        history = store.load_node_history(node_id="!node9001", window_hours=2, max_points=500)
        positions = history["positions"]

        assert len(positions) == 2
        assert [p["time_unix"] for p in positions] == [first, second]
        assert positions[0]["lat"] == pytest.approx(44.9701001, rel=0, abs=1e-9)
        assert positions[1]["lon"] == pytest.approx(-93.2645002, rel=0, abs=1e-9)
        assert history["summary"]["trail_points"] == 2
        assert history["summary"]["trail_start"] == md._format_epoch(first)
        assert history["summary"]["trail_end"] == md._format_epoch(second)
    finally:
        store.close()


def test_tracker_extracts_packet_position_and_persists_trail(tmp_path):
    store = _new_history_store(str(tmp_path / "tracker_position_history.sqlite3"))
    tracker = md.DashboardTracker(packet_limit=32, history_store=store)
    iface = types.SimpleNamespace(nodesByNum={})
    try:
        now = int(time.time())
        packet = {
            "id": now,
            "fromId": "!node99aa",
            "toId": "^all",
            "rxTime": now,
            "rxSnr": 5.5,
            "rxRssi": -97,
            "decoded": {
                "portnum": "POSITION_APP",
                "position": {
                    "latitudeI": 449706726,
                    "longitudeI": -932659313,
                    "altitude": 305.0,
                    "satsInView": 11,
                },
            },
        }
        tracker.on_receive(packet, iface)

        history = store.load_node_history(node_id="!node99aa", window_hours=1, max_points=120)
        assert len(history["positions"]) == 1
        point = history["positions"][0]
        assert point["lat"] == pytest.approx(44.9706726, rel=0, abs=1e-7)
        assert point["lon"] == pytest.approx(-93.2659313, rel=0, abs=1e-7)
        assert point["altitude"] == pytest.approx(305.0, rel=0, abs=1e-9)
        assert point["sats_in_view"] == 11
        assert history["summary"]["trail_points"] == 1
    finally:
        store.close()
