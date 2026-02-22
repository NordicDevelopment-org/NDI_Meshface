from meshdash.services import (
    build_node_history_loader,
    build_online_activity_loader,
    empty_node_history,
    empty_online_activity,
)


class _FakeHistoryStore:
    def __init__(self):
        self.node_calls = []
        self.online_calls = []

    def load_node_history(self, *, node_id, window_hours, max_points):
        self.node_calls.append((node_id, window_hours, max_points))
        return {"node_id": node_id, "window_hours": window_hours, "max_points": max_points}

    def load_online_activity(self, *, window_hours):
        self.online_calls.append(window_hours)
        return {"window_hours": window_hours, "points": []}


def test_empty_payload_shapes():
    node_empty = empty_node_history("!abc123")
    assert node_empty["node_id"] == "!abc123"
    assert node_empty["points"] == []
    assert node_empty["positions"] == []

    online_empty = empty_online_activity(12)
    assert online_empty["window_hours"] == 12
    assert len(online_empty["hourly_profile"]) == 24
    assert online_empty["summary"]["sample_hours"] == 0


def test_build_node_history_loader_defaults_and_overrides():
    store = _FakeHistoryStore()
    loader = build_node_history_loader(store, default_hours=72, default_points=1440)

    payload = loader(" !node1 ", None, None)
    assert payload["node_id"] == "!node1"
    assert payload["window_hours"] == 72
    assert payload["max_points"] == 1440

    payload = loader("!node2", 6, 120)
    assert payload["node_id"] == "!node2"
    assert payload["window_hours"] == 6
    assert payload["max_points"] == 120


def test_build_node_history_loader_without_store():
    loader = build_node_history_loader(None, default_hours=72, default_points=1440)
    payload = loader(" !xyz ", 5, 20)
    assert payload["node_id"] == "!xyz"
    assert payload["points"] == []
    assert payload["positions"] == []


def test_build_online_activity_loader_defaults_and_overrides():
    store = _FakeHistoryStore()
    loader = build_online_activity_loader(store, default_hours=72)

    payload = loader(None)
    assert payload["window_hours"] == 72

    payload = loader(24)
    assert payload["window_hours"] == 24
    assert store.online_calls == [72, 24]


def test_build_online_activity_loader_without_store():
    loader = build_online_activity_loader(None, default_hours=72)
    payload = loader(None)
    assert payload["window_hours"] == 72
    assert len(payload["hourly_profile"]) == 24
