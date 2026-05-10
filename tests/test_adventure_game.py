from types import SimpleNamespace

from meshdash.games.adventure import AdventureGame
from meshdash.services_adventure_bot import AdventureBotService
from meshdash.services_standalone_adventure import StandaloneAdventureService
from meshdash.tracker_runtime_impl import DashboardTracker


class _FakeInterface:
    def __init__(self) -> None:
        self.myInfo = {"my_node_num": 0x12345678}
        self.nodesByNum = {
            0x12345678: {"user": {"id": "!12345678"}},
            0x01020304: {"user": {"id": "!01020304"}},
        }
        self.sent: list[dict[str, object]] = []

    def sendText(self, text: str, **kwargs: object) -> object:
        packet = SimpleNamespace(id=1700 + len(self.sent))
        self.sent.append({"text": text, "kwargs": dict(kwargs), "packet": packet})
        return packet


def _direct_text_packet(text: str, *, to: int = 0x12345678, packet_id: int = 111) -> dict[str, object]:
    return {
        "from": 0x01020304,
        "to": to,
        "id": packet_id,
        "channel": 2,
        "decoded": {
            "portnum": "TEXT_MESSAGE_APP",
            "text": text,
        },
    }


def _play(game: AdventureGame, command: str, now: int) -> str:
    result = game.try_handle_message(
        text=command,
        from_id="!01020304",
        to_id="!12345678",
        local_node_id="!12345678",
        now_unix=now,
        enabled=True,
    )
    assert result.handled is True
    return str(result.reply_text or "")


def test_adventure_game_starts_and_uses_original_data() -> None:
    game = AdventureGame()

    start = _play(game, "adventure", 1)
    enter = _play(game, "enter", 2)

    assert "adventure: session started" in start
    assert "COLOSSAL CAVE" in start
    assert "WELL HOUSE" in enter
    assert "THERE IS A SHINY BRASS LAMP NEARBY" in enter


def test_adventure_game_takes_items_and_unlocks_grate() -> None:
    game = AdventureGame()
    commands = [
        "adventure",
        "enter",
        "take lamp",
        "take keys",
        "out",
        "downstream",
        "downstream",
        "downstream",
        "unlock grate",
        "down",
    ]

    replies = [_play(game, command, index + 1) for index, command in enumerate(commands)]

    assert replies[2] == "OK"
    assert replies[3] == "OK"
    assert "THE GRATE IS NOW UNLOCKED" in replies[-2]
    assert "BENEATH A 3X3 STEEL GRATE" in replies[-1]


def test_standalone_adventure_service_plays_console_session() -> None:
    service = StandaloneAdventureService()

    start = service.play(text="adventure", session_id="console-adventure")
    follow_up = service.play(text="enter", session_id="console-adventure")

    assert start["ok"] is True
    assert start["active_session"] is True
    assert "adventure: session started" in str(start["reply_text"])
    assert follow_up["ok"] is True
    assert "WELL HOUSE" in str(follow_up["reply_text"])


def test_adventure_bot_uses_shared_ack_transport() -> None:
    service = AdventureBotService(
        reply_segment_delay_seconds=0,
        reply_retry_limit=0,
        reply_async=False,
    )
    iface = _FakeInterface()

    handled = service.handle_packet(_direct_text_packet("adventure"), iface)

    assert handled is True
    assert iface.sent
    assert iface.sent[0]["kwargs"]["destinationId"] == "!01020304"
    assert iface.sent[0]["kwargs"]["wantAck"] is True
    assert iface.sent[0]["kwargs"]["replyId"] == 111
    assert "adventure: session started" in " ".join(str(row["text"]) for row in iface.sent)


def test_dashboard_tracker_answers_direct_adventure_when_enabled() -> None:
    tracker = DashboardTracker(packet_limit=25)
    iface = _FakeInterface()
    assert tracker.enable_adventure_bot(
        reply_segment_delay_seconds=0,
        reply_retry_limit=0,
        reply_async=False,
    ) is True

    tracker.on_receive(_direct_text_packet("adventure"), iface)

    assert iface.sent
    assert "adventure: session started" in " ".join(str(row["text"]) for row in iface.sent)
    runtime = tracker.get_zork_bot_runtime()
    assert runtime["adventure"]["enabled"] is True
    assert runtime["adventure"]["active_session_count"] == 1


def test_adventure_bot_retries_unacked_reply_segments() -> None:
    tracker = DashboardTracker(packet_limit=25)
    iface = _FakeInterface()
    assert tracker.enable_adventure_bot(
        reply_segment_delay_seconds=0,
        reply_ack_wait_seconds=0,
        reply_retry_limit=1,
        reply_async=False,
    ) is True

    tracker.on_receive(_direct_text_packet("adventure"), iface)

    assert len(iface.sent) >= 2
    assert iface.sent[0]["text"] == iface.sent[1]["text"]
    retry_entries = [
        row
        for row in tracker.recent_chat
        if isinstance(row, dict) and row.get("retry_of") == iface.sent[0]["packet"].id
    ]
    assert retry_entries
