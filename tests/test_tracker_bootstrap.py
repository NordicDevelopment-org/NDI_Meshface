from meshdash.tracker_bootstrap import TrackerHistoryBootstrap, load_tracker_history_bootstrap


class _FakeHistoryStore:
    def __init__(self):
        self.calls = []

    def load_recent_packets(self, limit):
        self.calls.append(("packets", limit))
        return [{"summary": {"packet_id": 1}}]

    def load_recent_chat(self, limit):
        self.calls.append(("chat", limit))
        return [{"message_id": 9}]

    def load_connections(self):
        self.calls.append(("connections", None))
        return [{"from": "!a", "to": "!b", "count": 2}]


def test_load_tracker_history_bootstrap_reads_history_and_builds_edges():
    store = _FakeHistoryStore()

    bootstrap = load_tracker_history_bootstrap(
        store,
        packet_limit=25,
        build_historical_edges_fn=lambda rows: {("!a", "!b"): {"count": rows[0]["count"]}},
    )

    assert isinstance(bootstrap, TrackerHistoryBootstrap)
    assert bootstrap.recent_packets == [{"summary": {"packet_id": 1}}]
    assert bootstrap.recent_chat == [{"message_id": 9}]
    assert bootstrap.historical_edges == {("!a", "!b"): {"count": 2}}
    assert store.calls == [("packets", 25), ("chat", 25), ("connections", None)]
