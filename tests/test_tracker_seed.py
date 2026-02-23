from meshdash.tracker_seed import seed_tracker_from_node_db


class _FakeTracker:
    def __init__(self):
        self.seeded = []

    def seed_packet(self, packet, iface):
        self.seeded.append((packet, iface))


def test_seed_tracker_from_node_db_filters_and_seeds_only_last_received_packets():
    tracker = _FakeTracker()
    iface = object()

    def _safe_items(_iface, retries, sleep_seconds):
        assert _iface is iface
        assert retries == 3
        assert sleep_seconds == 0.01
        yield 1, {"lastReceived": {"id": 11}}
        yield 2, {"lastReceived": None}
        yield 3, {"x": 1}
        yield 4, "not-a-dict"
        yield 5, {"lastReceived": {"id": 22}}

    seed_tracker_from_node_db(tracker, iface, safe_nodes_items_fn=_safe_items)

    assert tracker.seeded == [
        ({"id": 11}, iface),
        ({"id": 22}, iface),
    ]
