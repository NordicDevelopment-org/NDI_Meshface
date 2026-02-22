import time
from datetime import datetime

import mesh_dashboard as md


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
