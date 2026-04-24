from pathlib import Path
from types import SimpleNamespace

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.services_bbs_host import build_bbs_host_service


def _make_iface(*, local_num: int, sender_num: int, sender_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        myInfo={"myNodeNum": local_num},
        nodesByNum={
            local_num: {"user": {"id": f"!{local_num:08x}"}},
            sender_num: {"user": {"id": sender_id}},
        },
    )


def test_bbs_host_service_replies_to_direct_open_requests() -> None:
    sent_messages: list[dict[str, object]] = []
    stored_posts = [
        {
            "entry_id": "post-1",
            "author_id": "!12345678",
            "author_name": "Zorkbot",
            "text": "hello board",
            "unix": 101,
        }
    ]

    service = build_bbs_host_service(
        local_node_id_fn=lambda: "!12345678",
        send_chat_fn=lambda **kwargs: sent_messages.append(dict(kwargs)) or {"ok": True},
        get_bbs_posts_fn=lambda: {"ok": True, "posts": stored_posts},
        now_unix_fn=lambda: 111,
        send_spacing_seconds=0,
    )

    started = service.start(
        SimpleNamespace(
            channel_index=2,
            title="Node Space",
            board_id="node-space",
            motd="hello world",
        )
    )

    assert started["ok"] is True
    assert started["host"]["enabled"] is True
    assert started["host"]["board_id"] == "node-space"

    iface = _make_iface(local_num=0x12345678, sender_num=0x01020304, sender_id="!01020304")
    packet = {
        "from": 0x01020304,
        "to": 0x12345678,
        "channel": 4,
        "decoded": {"text": "bbs1|open|token123", "portnum": "TEXT_MESSAGE_APP"},
    }

    service.on_receive(packet, iface)
    assert service.wait_for_idle(1.0) is True

    assert sent_messages == [
        {
            "text": "bbs1|profile|token123|node-space|!12345678|Node Space|hello world",
            "destination": "!01020304",
            "channel_index": 4,
        },
        {
            "text": "bbs1|post|node-space|!12345678|post-1|!12345678|Zorkbot|hello board",
            "destination": "!01020304",
            "channel_index": 4,
        },
    ]


def test_bbs_host_service_status_tracks_start_and_stop() -> None:
    service = build_bbs_host_service(
        local_node_id_fn=lambda: "!87654321",
        send_chat_fn=lambda **_kwargs: {"ok": True},
        now_unix_fn=lambda: 222,
        send_spacing_seconds=0,
    )

    initial = service.get_runtime()
    assert initial["ok"] is True
    assert initial["host"]["enabled"] is False
    assert initial["host"]["title"] == "Packet Exchange"

    started = service.start(
        SimpleNamespace(
            channel_index=5,
            title="Grid BBS",
            board_id="grid-bbs",
            motd="online",
        )
    )
    assert started["host"]["enabled"] is True
    assert started["host"]["host_id"] == "!87654321"
    assert started["host"]["channel_index"] == 5
    assert started["host"]["started_unix"] == 222

    stopped = service.stop()
    assert stopped["host"]["enabled"] is False
    assert stopped["host"]["started_unix"] == 0
    assert stopped["host"]["host_id"] == "!87654321"


def test_bbs_host_service_persists_posts_from_direct_messages_and_local_control_panel() -> None:
    stored_posts: list[dict[str, object]] = []
    sent_messages: list[dict[str, object]] = []

    def _append_bbs_post(post: object) -> dict[str, object]:
        payload = dict(post) if isinstance(post, dict) else {}
        stored_posts.append(payload)
        return {"ok": True, "post": payload, "posts": list(stored_posts)}

    service = build_bbs_host_service(
        local_node_id_fn=lambda: "!12345678",
        send_chat_fn=lambda **kwargs: sent_messages.append(dict(kwargs)) or {"ok": True},
        get_bbs_posts_fn=lambda: {"ok": True, "posts": list(stored_posts)},
        append_bbs_post_fn=_append_bbs_post,
        now_unix_fn=lambda: 333,
        send_spacing_seconds=0,
    )
    service.start(
        SimpleNamespace(
            channel_index=2,
            title="Node Space",
            board_id="node-space",
            motd="hello world",
        )
    )

    iface = _make_iface(local_num=0x12345678, sender_num=0x01020304, sender_id="!01020304")
    packet = {
        "from": 0x01020304,
        "to": 0x12345678,
        "channel": 4,
        "decoded": {"text": "bbs1|post|node-space|!12345678|remote-1|!01020304|Remote|cant see the posts"},
    }

    service.on_receive(packet, iface)
    posted = service.append_post(
        SimpleNamespace(
            text="local reply",
            author_name="zorkbot",
            entry_id="local-1",
        )
    )
    assert service.wait_for_idle(1.0) is True

    assert posted["ok"] is True
    assert [row["text"] for row in stored_posts] == [
        "cant see the posts",
        "local reply",
    ]
    assert [row["text"] for row in sent_messages] == [
        "bbs1|post|node-space|!12345678|remote-1|!01020304|Remote|cant see the posts",
        "bbs1|post|node-space|!12345678|local-1|!12345678|zorkbot|local reply",
    ]


def test_bbs_host_service_fanouts_new_posts_to_clients_after_open() -> None:
    sent_messages: list[dict[str, object]] = []
    stored_posts: list[dict[str, object]] = [
        {
            "entry_id": "old-1",
            "author_id": "!12345678",
            "author_name": "zorkbot",
            "text": "older post",
            "unix": 100,
        }
    ]

    def _append_bbs_post(post: object) -> dict[str, object]:
        payload = dict(post) if isinstance(post, dict) else {}
        stored_posts.append(payload)
        return {"ok": True, "post": payload, "posts": list(stored_posts)}

    service = build_bbs_host_service(
        local_node_id_fn=lambda: "!12345678",
        send_chat_fn=lambda **kwargs: sent_messages.append(dict(kwargs)) or {"ok": True},
        get_bbs_posts_fn=lambda: {"ok": True, "posts": list(stored_posts)},
        append_bbs_post_fn=_append_bbs_post,
        now_unix_fn=lambda: 444,
        send_spacing_seconds=0,
    )
    service.start(
        SimpleNamespace(
            channel_index=2,
            title="Node Space",
            board_id="node-space",
            motd="hello world",
        )
    )

    iface = _make_iface(local_num=0x12345678, sender_num=0x01020304, sender_id="!01020304")
    open_packet = {
        "from": 0x01020304,
        "to": 0x12345678,
        "channel": 4,
        "decoded": {"text": "bbs1|open|token123", "portnum": "TEXT_MESSAGE_APP"},
    }

    service.on_receive(open_packet, iface)
    assert service.wait_for_idle(1.0) is True

    posted = service.append_post(
        SimpleNamespace(
            text="fresh post",
            author_name="zorkbot",
            entry_id="fresh-1",
        )
    )
    assert posted["ok"] is True
    assert service.wait_for_idle(1.0) is True

    assert [row["text"] for row in sent_messages] == [
        "bbs1|profile|token123|node-space|!12345678|Node Space|hello world",
        "bbs1|post|node-space|!12345678|old-1|!12345678|zorkbot|older post",
        "bbs1|post|node-space|!12345678|fresh-1|!12345678|zorkbot|fresh post",
    ]


def test_bbs_host_service_waits_for_delivery_before_sending_next_packet() -> None:
    sent_messages: list[dict[str, object]] = []
    call_sequence: list[str] = []
    state_calls: dict[int, int] = {}
    stored_posts = [
        {
            "entry_id": "post-1",
            "author_id": "!12345678",
            "author_name": "Zorkbot",
            "text": "hello board",
            "unix": 101,
        }
    ]
    next_message_id = 900

    def _send_chat(**kwargs: object) -> dict[str, object]:
        nonlocal next_message_id
        sent_messages.append(dict(kwargs))
        call_sequence.append(f"send:{next_message_id}")
        message_id = next_message_id
        next_message_id += 1
        return {"ok": True, "message_id": message_id}

    def _get_delivery_state(message_id: object) -> dict[str, object]:
        clean_id = int(message_id or 0)
        state_calls[clean_id] = state_calls.get(clean_id, 0) + 1
        call_sequence.append(f"state:{clean_id}:{state_calls[clean_id]}")
        if state_calls[clean_id] >= 2:
            return {"delivery_state": "acked"}
        return {"delivery_state": "pending"}

    service = build_bbs_host_service(
        local_node_id_fn=lambda: "!12345678",
        send_chat_fn=_send_chat,
        get_bbs_posts_fn=lambda: {"ok": True, "posts": stored_posts},
        get_delivery_state_fn=_get_delivery_state,
        now_unix_fn=lambda: 111,
        send_spacing_seconds=0,
        delivery_wait_timeout_seconds=1.0,
        delivery_poll_seconds=0,
    )
    service.start(
        SimpleNamespace(
            channel_index=2,
            title="Node Space",
            board_id="node-space",
            motd="hello world",
        )
    )

    iface = _make_iface(local_num=0x12345678, sender_num=0x01020304, sender_id="!01020304")
    packet = {
        "from": 0x01020304,
        "to": 0x12345678,
        "channel": 4,
        "decoded": {"text": "bbs1|open|token123", "portnum": "TEXT_MESSAGE_APP"},
    }

    service.on_receive(packet, iface)
    assert service.wait_for_idle(1.0) is True

    assert sent_messages == [
        {
            "text": "bbs1|profile|token123|node-space|!12345678|Node Space|hello world",
            "destination": "!01020304",
            "channel_index": 4,
        },
        {
            "text": "bbs1|post|node-space|!12345678|post-1|!12345678|Zorkbot|hello board",
            "destination": "!01020304",
            "channel_index": 4,
        },
    ]
    assert call_sequence[:4] == [
        "send:900",
        "state:900:1",
        "state:900:2",
        "send:901",
    ]


def test_bbs_host_service_retries_unsettled_delivery_before_advancing_queue() -> None:
    sent_messages: list[dict[str, object]] = []
    call_sequence: list[str] = []
    message_state_by_id = {
        900: "unsettled",
        901: "acked",
        902: "acked",
    }
    next_message_id = 900
    stored_posts = [
        {
            "entry_id": "post-1",
            "author_id": "!12345678",
            "author_name": "Zorkbot",
            "text": "hello board",
            "unix": 101,
        }
    ]

    def _send_chat(**kwargs: object) -> dict[str, object]:
        nonlocal next_message_id
        sent_messages.append(dict(kwargs))
        call_sequence.append(f"send:{next_message_id}:{kwargs.get('text')}")
        message_id = next_message_id
        next_message_id += 1
        return {"ok": True, "message_id": message_id}

    def _get_delivery_state(message_id: object) -> dict[str, object]:
        clean_id = int(message_id or 0)
        call_sequence.append(f"state:{clean_id}")
        state = message_state_by_id.get(clean_id, "acked")
        return {"delivery_state": "" if state == "unsettled" else state}

    service = build_bbs_host_service(
        local_node_id_fn=lambda: "!12345678",
        send_chat_fn=_send_chat,
        get_bbs_posts_fn=lambda: {"ok": True, "posts": stored_posts},
        get_delivery_state_fn=_get_delivery_state,
        now_unix_fn=lambda: 111,
        send_spacing_seconds=0,
        delivery_wait_timeout_seconds=0.01,
        delivery_poll_seconds=0.01,
        retry_backoff_seconds=0,
    )
    service.start(
        SimpleNamespace(
            channel_index=2,
            title="Node Space",
            board_id="node-space",
            motd="hello world",
        )
    )

    iface = _make_iface(local_num=0x12345678, sender_num=0x01020304, sender_id="!01020304")
    packet = {
        "from": 0x01020304,
        "to": 0x12345678,
        "channel": 4,
        "decoded": {"text": "bbs1|open|token123", "portnum": "TEXT_MESSAGE_APP"},
    }

    service.on_receive(packet, iface)
    assert service.wait_for_idle(1.0) is True

    assert [row["text"] for row in sent_messages] == [
        "bbs1|profile|token123|node-space|!12345678|Node Space|hello world",
        "bbs1|profile|token123|node-space|!12345678|Node Space|hello world",
        "bbs1|post|node-space|!12345678|post-1|!12345678|Zorkbot|hello board",
    ]
    assert call_sequence[:5] == [
        "send:900:bbs1|profile|token123|node-space|!12345678|Node Space|hello world",
        "state:900",
        "send:901:bbs1|profile|token123|node-space|!12345678|Node Space|hello world",
        "state:901",
        "send:902:bbs1|post|node-space|!12345678|post-1|!12345678|Zorkbot|hello board",
    ]
