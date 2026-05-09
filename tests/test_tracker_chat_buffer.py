from meshdash.tracker_bootstrap import load_tracker_history_bootstrap
from meshdash.tracker_setup import initialize_tracker_buffers


class _HistoryStore:
    def __init__(self) -> None:
        self.packet_limit = 0
        self.chat_limit = 0

    def load_recent_packets(self, limit: int) -> list[dict[str, object]]:
        self.packet_limit = limit
        return []

    def load_recent_chat(self, limit: int) -> list[dict[str, object]]:
        self.chat_limit = limit
        return []

    def load_connections(self) -> list[dict[str, object]]:
        return []


def test_recent_chat_buffer_is_larger_than_packet_buffer() -> None:
    buffers = initialize_tracker_buffers(250)

    assert buffers.recent_packets.maxlen == 250
    assert buffers.recent_chat.maxlen == 1000


def test_history_bootstrap_loads_larger_recent_chat_window() -> None:
    history_store = _HistoryStore()

    load_tracker_history_bootstrap(
        history_store,
        packet_limit=250,
        build_historical_edges_fn=lambda _rows: {},
    )

    assert history_store.packet_limit == 250
    assert history_store.chat_limit == 1000
