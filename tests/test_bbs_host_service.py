import base64
import json
from pathlib import Path
from types import SimpleNamespace

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.services_bbs_host import build_bbs_host_service


def _sent_texts(sent_messages: list[dict[str, object]]) -> list[str]:
    return [str(row.get("text") or "") for row in sent_messages]


def _decode_snapshot_from_sent(sent_messages: list[dict[str, object]]) -> dict[str, object]:
    texts = _sent_texts(sent_messages)
    meta = next(text for text in texts if text.startswith("MF_FILE_V1|M|"))
    parts = meta.split("|")
    transfer_id = parts[2]
    file_size = int(parts[4])
    total_chunks = int(parts[5])
    chunks: dict[int, bytes] = {}
    for text in texts:
        if not text.startswith(f"MF_FILE_V1|C|{transfer_id}|"):
            continue
        chunk_parts = text.split("|")
        chunks[int(chunk_parts[3])] = base64.b64decode(chunk_parts[4])
    assert sorted(chunks) == list(range(total_chunks))
    payload = b"".join(chunks[idx] for idx in range(total_chunks))[:file_size]
    decoded = json.loads(payload.decode("utf-8"))
    assert isinstance(decoded, dict)
    return decoded


def _snapshot_transfer_meta(sent_messages: list[dict[str, object]]) -> tuple[str, int]:
    meta = next(text for text in _sent_texts(sent_messages) if text.startswith("MF_FILE_V1|M|"))
    parts = meta.split("|")
    return parts[2], int(parts[5])


def _file_ack_frame(transfer_id: str, total_chunks: int, received_indexes: set[int]) -> str:
    bitmap = bytearray(max(1, (total_chunks + 7) // 8))
    for idx in received_indexes:
        bitmap[idx // 8] |= 1 << (idx % 8)
    return (
        f"MF_FILE_V1|A|{transfer_id}|{len(received_indexes)}|{total_chunks}|"
        f"{base64.b64encode(bytes(bitmap)).decode('ascii')}"
    )


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
            "author_name": "Demo Relay",
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

    texts = _sent_texts(sent_messages)
    assert texts[0] == "bbs1|profile|token123|node-space|!12345678|Node Space|hello world|1|101|post-1"
    assert texts[1].startswith("MF_FILE_V1|M|")
    assert all(row["destination"] == "!01020304" for row in sent_messages)
    assert all(row["channel_index"] == 4 for row in sent_messages)
    snapshot = _decode_snapshot_from_sent(sent_messages)
    assert snapshot["kind"] == "easyface-bbs-snapshot-v1"
    assert snapshot["board_id"] == "node-space"
    assert snapshot["host_id"] == "!12345678"
    assert snapshot["post_count"] == 1
    assert snapshot["posts"] == [["post-1", "!12345678", "Demo Relay", "hello board", 101]]


def test_bbs_host_service_open_cursor_sends_only_missing_posts() -> None:
    sent_messages: list[dict[str, object]] = []
    stored_posts = [
        {
            "entry_id": "post-1",
            "author_id": "!12345678",
            "author_name": "Demo Relay",
            "text": "first",
            "unix": 100,
        },
        {
            "entry_id": "post-2",
            "author_id": "!12345678",
            "author_name": "Demo Relay",
            "text": "second",
            "unix": 101,
        },
        {
            "entry_id": "post-3",
            "author_id": "!12345678",
            "author_name": "Demo Relay",
            "text": "third",
            "unix": 102,
        },
    ]

    service = build_bbs_host_service(
        local_node_id_fn=lambda: "!12345678",
        send_chat_fn=lambda **kwargs: sent_messages.append(dict(kwargs)) or {"ok": True},
        get_bbs_posts_fn=lambda: {"ok": True, "posts": stored_posts},
        now_unix_fn=lambda: 111,
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
        "decoded": {"text": "bbs1|open|token123|node-space|101|post-2"},
    }

    service.on_receive(packet, iface)
    assert service.wait_for_idle(1.0) is True

    texts = _sent_texts(sent_messages)
    assert texts[0] == "bbs1|profile|token123|node-space|!12345678|Node Space|hello world|3|102|post-3"
    snapshot = _decode_snapshot_from_sent(sent_messages)
    assert snapshot["posts"] == [["post-3", "!12345678", "Demo Relay", "third", 102]]


def test_bbs_host_service_batches_short_history_posts() -> None:
    sent_messages: list[dict[str, object]] = []
    stored_posts = [
        {
            "entry_id": "post-1",
            "author_id": "!12345678",
            "author_name": "Demo Relay",
            "text": "first",
            "unix": 100,
        },
        {
            "entry_id": "post-2",
            "author_id": "!12345678",
            "author_name": "Demo Relay",
            "text": "second",
            "unix": 101,
        },
        {
            "entry_id": "post-3",
            "author_id": "!12345678",
            "author_name": "Demo Relay",
            "text": "third",
            "unix": 102,
        },
    ]

    service = build_bbs_host_service(
        local_node_id_fn=lambda: "!12345678",
        send_chat_fn=lambda **kwargs: sent_messages.append(dict(kwargs)) or {"ok": True},
        get_bbs_posts_fn=lambda: {"ok": True, "posts": stored_posts},
        now_unix_fn=lambda: 111,
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
        "decoded": {"text": "bbs1|open|token123"},
    }

    service.on_receive(packet, iface)
    assert service.wait_for_idle(1.0) is True

    assert sent_messages[0]["text"] == (
        "bbs1|profile|token123|node-space|!12345678|Node Space|hello world|3|102|post-3"
    )
    assert len(sent_messages) > 2
    assert str(sent_messages[1]["text"]).startswith("MF_FILE_V1|M|")
    assert all(len(str(row["text"]).encode("utf-8")) <= 200 for row in sent_messages)
    snapshot = _decode_snapshot_from_sent(sent_messages)
    assert [row[3] for row in snapshot["posts"]] == ["first", "second", "third"]


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


def test_bbs_host_service_persists_and_restores_runtime_state() -> None:
    stored_settings: dict[str, object] = {}

    def _set_settings(settings: object) -> dict[str, object]:
        assert isinstance(settings, dict)
        stored_settings.update(settings)
        return {"ok": True, "settings": dict(stored_settings)}

    service = build_bbs_host_service(
        local_node_id_fn=lambda: "!87654321",
        send_chat_fn=lambda **_kwargs: {"ok": True},
        get_bbs_settings_fn=lambda: {"ok": True, "settings": dict(stored_settings)},
        set_bbs_settings_fn=_set_settings,
        now_unix_fn=lambda: 222,
        send_spacing_seconds=0,
    )

    started = service.start(
        SimpleNamespace(
            channel_index=5,
            title="Grid BBS",
            board_id="grid-bbs",
            motd="online",
        )
    )

    assert started["host"]["enabled"] is True
    assert stored_settings["enabled"] is True
    assert stored_settings["channel_index"] == 5
    assert stored_settings["started_unix"] == 222

    restored_service = build_bbs_host_service(
        local_node_id_fn=lambda: "!87654321",
        send_chat_fn=lambda **_kwargs: {"ok": True},
        get_bbs_settings_fn=lambda: {"ok": True, "settings": dict(stored_settings)},
        set_bbs_settings_fn=_set_settings,
        now_unix_fn=lambda: 999,
        send_spacing_seconds=0,
    )
    restored = restored_service.restore_persisted_runtime()

    assert restored["host"]["enabled"] is True
    assert restored["host"]["channel_index"] == 5
    assert restored["host"]["started_unix"] == 222

    stopped = restored_service.stop()

    assert stopped["host"]["enabled"] is False
    assert stored_settings["enabled"] is False
    assert stored_settings["started_unix"] == 0


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
        "decoded": {"text": "bbs1|post|node-space|!12345678|remote-1|!01020304|Remote|cant see the posts|123"},
    }

    service.on_receive(packet, iface)
    posted = service.append_post(
        SimpleNamespace(
            text="local reply",
            author_name="demo relay",
            entry_id="local-1",
        )
    )
    assert service.wait_for_idle(1.0) is True

    assert posted["ok"] is True
    assert [row["text"] for row in stored_posts] == [
        "cant see the posts",
        "local reply",
    ]
    assert [row["unix"] for row in stored_posts] == [333, 333]
    assert [row["text"] for row in sent_messages] == [
        "bbs1|post|node-space|!12345678|remote-1|!01020304|Remote|cant see the posts|333",
        "bbs1|post|node-space|!12345678|local-1|!12345678|demo relay|local reply|333",
    ]


def test_bbs_host_service_fanouts_new_posts_to_clients_after_open() -> None:
    sent_messages: list[dict[str, object]] = []
    stored_posts: list[dict[str, object]] = [
        {
            "entry_id": "old-1",
            "author_id": "!12345678",
            "author_name": "demo relay",
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
            author_name="demo relay",
            entry_id="fresh-1",
        )
    )
    assert posted["ok"] is True
    assert service.wait_for_idle(1.0) is True

    texts = _sent_texts(sent_messages)
    assert texts[0] == "bbs1|profile|token123|node-space|!12345678|Node Space|hello world|1|100|old-1"
    snapshot = _decode_snapshot_from_sent(sent_messages)
    assert snapshot["posts"] == [["old-1", "!12345678", "demo relay", "older post", 100]]
    assert texts[-1] == "bbs1|post|node-space|!12345678|fresh-1|!12345678|demo relay|fresh post|444"


def test_bbs_host_service_streams_history_snapshot_without_delivery_wait() -> None:
    sent_messages: list[dict[str, object]] = []
    call_sequence: list[str] = []
    state_calls: dict[int, int] = {}
    stored_posts = [
        {
            "entry_id": "post-1",
            "author_id": "!12345678",
            "author_name": "Demo Relay",
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

    texts = _sent_texts(sent_messages)
    assert texts[0] == "bbs1|profile|token123|node-space|!12345678|Node Space|hello world|1|101|post-1"
    assert texts[1].startswith("MF_FILE_V1|M|")
    assert call_sequence[:2] == [
        "send:900",
        "send:901",
    ]
    assert state_calls == {}


def test_bbs_host_service_does_not_retry_unsettled_history_snapshot() -> None:
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
            "author_name": "Demo Relay",
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

    texts = _sent_texts(sent_messages)
    assert texts[0] == "bbs1|profile|token123|node-space|!12345678|Node Space|hello world|1|101|post-1"
    assert texts[1].startswith("MF_FILE_V1|M|")
    assert call_sequence[:2] == [
        "send:900:bbs1|profile|token123|node-space|!12345678|Node Space|hello world|1|101|post-1",
        f"send:901:{texts[1]}",
    ]


def test_bbs_host_service_requeues_missing_snapshot_chunks_from_file_ack() -> None:
    sent_messages: list[dict[str, object]] = []
    stored_posts = [
        {
            "entry_id": f"post-{idx}",
            "author_id": "!12345678",
            "author_name": "Demo Relay",
            "text": f"message {idx}",
            "unix": 100 + idx,
        }
        for idx in range(5)
    ]

    service = build_bbs_host_service(
        local_node_id_fn=lambda: "!12345678",
        send_chat_fn=lambda **kwargs: sent_messages.append(dict(kwargs)) or {"ok": True},
        get_bbs_posts_fn=lambda: {"ok": True, "posts": stored_posts},
        now_unix_fn=lambda: 111,
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
    service.on_receive(
        {
            "from": 0x01020304,
            "to": 0x12345678,
            "channel": 4,
            "decoded": {"text": "bbs1|open|token123", "portnum": "TEXT_MESSAGE_APP"},
        },
        iface,
    )
    assert service.wait_for_idle(1.0) is True
    transfer_id, total_chunks = _snapshot_transfer_meta(sent_messages)
    before_ack_count = len(sent_messages)

    service.on_receive(
        {
            "from": 0x01020304,
            "to": 0x12345678,
            "channel": 4,
            "decoded": {
                "text": _file_ack_frame(transfer_id, total_chunks, {0}),
                "portnum": "TEXT_MESSAGE_APP",
            },
        },
        iface,
    )
    assert service.wait_for_idle(1.0) is True

    resent_texts = _sent_texts(sent_messages[before_ack_count:])
    assert resent_texts[0].startswith(f"MF_FILE_V1|M|{transfer_id}|")
    resent_chunk_indexes = {
        int(text.split("|")[3])
        for text in resent_texts[1:]
        if text.startswith(f"MF_FILE_V1|C|{transfer_id}|")
    }
    assert resent_chunk_indexes == set(range(1, total_chunks))
