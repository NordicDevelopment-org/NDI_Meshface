import re
import threading
import time
from collections import deque
from collections.abc import Mapping

from .helpers import to_int as _to_int
from .helpers_node_names import normalize_node_id_text as _normalize_node_id_text
from .nodes_identity import get_local_node_num as _get_local_node_num

_BBS_PROTOCOL_VERSION = "bbs1"
_BBS_MAX_POST_HISTORY_REPLY = 32
_BBS_MAX_SUBSCRIBERS = 24
_BBS_SUBSCRIBER_TTL_SECONDS = 20 * 60
_BBS_SEND_SPACING_SECONDS = 0.45
_BBS_DELIVERY_WAIT_TIMEOUT_SECONDS = 4.5
_BBS_DELIVERY_POLL_SECONDS = 0.15
_BBS_MAX_SEND_ATTEMPTS = 3
_BBS_RETRY_BACKOFF_SECONDS = 1.0


def _sanitize_bbs_text(value: object, max_chars: int) -> str:
    limit = max(1, int(max_chars))
    return (
        " ".join(str(value if value is not None else "").replace("|", " ").split())
        .strip()
        [:limit]
    )


def _normalize_bbs_board_id(value: object, fallback: object = "") -> str:
    text = str(value or fallback or "").strip().lower()
    text = re.sub(r"[^a-z0-9_-]+", "-", text)
    text = re.sub(r"-+", "-", text)
    text = re.sub(r"^[-_]+|[-_]+$", "", text)
    return text[:24]


def _normalize_bbs_settings(payload: object) -> dict[str, object]:
    source = payload if isinstance(payload, Mapping) else {}
    title = _sanitize_bbs_text(source.get("title"), 42) or "Packet Exchange"
    board_id = _normalize_bbs_board_id(
        source.get("board_id", source.get("boardId")),
        title,
    )
    motd = _sanitize_bbs_text(source.get("motd"), 120) or "2400 baud online."
    return {
        "title": title,
        "board_id": board_id,
        "motd": motd,
    }


def _normalize_channel_index(value: object, *, fallback: int = 0) -> int:
    candidate = _to_int(value)
    if candidate is None or candidate < 0:
        return max(0, int(fallback))
    return int(candidate)


def _is_canonical_node_id(value: object) -> bool:
    text = _normalize_node_id_text(value)
    return bool(text.startswith("!") and len(text) == 9)


def _normalize_request_settings(request: object) -> dict[str, object]:
    return _normalize_bbs_settings(
        {
            "title": getattr(request, "title", None),
            "board_id": getattr(request, "board_id", None),
            "motd": getattr(request, "motd", None),
        }
    )


def _generate_post_entry_id(now_unix: int, author_id: str, text: str) -> str:
    seed = f"{now_unix}|{author_id}|{text}"
    return f"bbs-{now_unix:x}-{abs(hash(seed)) & 0xFFFFFFFF:08x}"


def _normalize_post_payload(payload: object) -> dict[str, object] | None:
    source = payload if isinstance(payload, Mapping) else {}
    text = _sanitize_bbs_text(source.get("text"), 220)
    if not text:
        return None
    author_id = _normalize_node_id_text(source.get("author_id", source.get("authorId")))
    if not _is_canonical_node_id(author_id):
        author_id = ""
    author_name = _sanitize_bbs_text(
        source.get("author_name", source.get("authorName")),
        48,
    )
    entry_id = _sanitize_bbs_text(
        source.get("entry_id", source.get("entryId")),
        60,
    )
    try:
        unix_value = int(source.get("unix") or 0)
    except Exception:
        unix_value = 0
    unix_value = max(0, unix_value)
    if not entry_id:
        entry_id = _generate_post_entry_id(unix_value, author_id, text)
    return {
        "entry_id": entry_id,
        "author_id": author_id,
        "author_name": author_name or author_id or "anon",
        "text": text,
        "unix": unix_value,
    }


def _extract_packet_text(packet: object) -> str:
    if not isinstance(packet, Mapping):
        return ""
    decoded = packet.get("decoded")
    if isinstance(decoded, Mapping):
        text = decoded.get("text")
        if isinstance(text, str):
            return text.strip()
    text = packet.get("decoded_text")
    if isinstance(text, str):
        return text.strip()
    return ""


def _parse_protocol_message(text: object) -> tuple[str, list[str]] | None:
    raw = str(text or "").strip()
    if not raw or not raw.startswith(f"{_BBS_PROTOCOL_VERSION}|"):
        return None
    parts = [str(part or "").strip() for part in raw.split("|")]
    if len(parts) < 2:
        return None
    message_type = str(parts[1] or "").strip().lower()
    if not message_type:
        return None
    return message_type, parts


def _encode_protocol_message(message_type: object, *fields: object) -> str:
    clean_type = str(message_type or "").strip().lower()
    if not clean_type:
        return ""
    encoded = [_BBS_PROTOCOL_VERSION, clean_type]
    for field in fields:
        encoded.append(_sanitize_bbs_text(field, 220))
    return "|".join(encoded)


class BbsHostService:
    def __init__(
        self,
        *,
        local_node_id_fn,
        send_chat_fn,
        get_bbs_settings_fn=None,
        set_bbs_settings_fn=None,
        get_bbs_posts_fn=None,
        append_bbs_post_fn=None,
        get_delivery_state_fn=None,
        now_unix_fn=time.time,
        send_spacing_seconds: float = _BBS_SEND_SPACING_SECONDS,
        subscriber_ttl_seconds: int = _BBS_SUBSCRIBER_TTL_SECONDS,
        delivery_wait_timeout_seconds: float = _BBS_DELIVERY_WAIT_TIMEOUT_SECONDS,
        delivery_poll_seconds: float = _BBS_DELIVERY_POLL_SECONDS,
        max_send_attempts: int = _BBS_MAX_SEND_ATTEMPTS,
        retry_backoff_seconds: float = _BBS_RETRY_BACKOFF_SECONDS,
    ) -> None:
        self._lock = threading.Lock()
        self._send_cond = threading.Condition()
        self._local_node_id_fn = local_node_id_fn
        self._send_chat_fn = send_chat_fn
        self._get_bbs_settings_fn = get_bbs_settings_fn
        self._set_bbs_settings_fn = set_bbs_settings_fn
        self._get_bbs_posts_fn = get_bbs_posts_fn
        self._append_bbs_post_fn = append_bbs_post_fn
        self._get_delivery_state_fn = get_delivery_state_fn
        self._now_unix_fn = now_unix_fn
        self._send_spacing_seconds = max(0.0, float(send_spacing_seconds))
        self._subscriber_ttl_seconds = max(60, int(subscriber_ttl_seconds))
        self._delivery_wait_timeout_seconds = max(0.0, float(delivery_wait_timeout_seconds))
        self._delivery_poll_seconds = max(0.01, float(delivery_poll_seconds))
        self._max_send_attempts = max(1, int(max_send_attempts))
        self._retry_backoff_seconds = max(0.0, float(retry_backoff_seconds))
        self._enabled = False
        self._channel_index = 0
        self._started_unix = 0
        self._settings_cache = _normalize_bbs_settings({})
        self._posts_cache: list[dict[str, object]] = []
        self._subscribers_by_id: dict[str, dict[str, int]] = {}
        self._outbound_queue: deque[dict[str, object]] = deque()
        self._outbound_sending = False
        self._outbound_shutdown = False
        self._outbound_next_send_monotonic = 0.0
        self._outbound_thread = threading.Thread(
            target=self._outbound_loop,
            name="bbs-host-send",
            daemon=True,
        )
        self._outbound_thread.start()

    def _load_settings(self) -> dict[str, object]:
        getter = self._get_bbs_settings_fn
        if callable(getter):
            try:
                payload = getter()
            except Exception:
                payload = None
            if isinstance(payload, Mapping):
                raw_settings = payload.get("settings", payload)
                normalized = _normalize_bbs_settings(raw_settings)
                with self._lock:
                    self._settings_cache = dict(normalized)
                return normalized
        with self._lock:
            return dict(self._settings_cache)

    def _save_settings(self, request: object | None) -> dict[str, object]:
        normalized = _normalize_request_settings(request)
        setter = self._set_bbs_settings_fn
        if callable(setter):
            response = setter(
                {
                    "title": normalized["title"],
                    "board_id": normalized["board_id"],
                    "motd": normalized["motd"],
                }
            )
            if isinstance(response, Mapping):
                raw_settings = response.get("settings", response)
                normalized = _normalize_bbs_settings(raw_settings)
        with self._lock:
            self._settings_cache = dict(normalized)
        return normalized

    def _load_posts(self) -> list[dict[str, object]]:
        getter = self._get_bbs_posts_fn
        if callable(getter):
            try:
                payload = getter()
            except Exception:
                payload = None
            if isinstance(payload, Mapping):
                source = payload.get("posts", payload)
                if isinstance(source, list):
                    rows = [_normalize_post_payload(row) for row in source]
                    normalized = [row for row in rows if row]
                    with self._lock:
                        self._posts_cache = list(normalized)
                    return list(normalized)
        with self._lock:
            return list(self._posts_cache)

    def _append_post(self, post: object) -> dict[str, object]:
        normalized = _normalize_post_payload(post)
        if normalized is None:
            raise ValueError("BBS post text is required")
        setter = self._append_bbs_post_fn
        if callable(setter):
            response = setter(normalized)
            if isinstance(response, Mapping):
                payload_post = response.get("post", normalized)
                loaded_post = _normalize_post_payload(payload_post)
                if loaded_post:
                    normalized = loaded_post
                payload_posts = response.get("posts")
                if isinstance(payload_posts, list):
                    normalized_posts = [_normalize_post_payload(row) for row in payload_posts]
                    with self._lock:
                        self._posts_cache = [row for row in normalized_posts if row]
                    return dict(normalized)
        with self._lock:
            rows = list(self._posts_cache)
            entry_id = str(normalized.get("entry_id") or "").strip()
            if not any(str(row.get("entry_id") or "").strip() == entry_id for row in rows):
                rows.append(normalized)
            rows.sort(key=lambda row: (int(row.get("unix") or 0), str(row.get("entry_id") or "")))
            self._posts_cache = rows[-260:]
        return dict(normalized)

    def _status_payload(self) -> dict[str, object]:
        settings = self._load_settings()
        local_id = _normalize_node_id_text(self._local_node_id_fn())
        with self._lock:
            enabled = bool(self._enabled)
            started_unix = int(self._started_unix)
            channel_index = int(self._channel_index)
        return {
            "enabled": enabled,
            "title": settings["title"],
            "board_id": settings["board_id"],
            "motd": settings["motd"],
            "started_unix": started_unix if enabled else 0,
            "channel_index": channel_index,
            "host_id": local_id if _is_canonical_node_id(local_id) else "",
        }

    def _remember_subscriber(
        self,
        subscriber_id: object,
        *,
        channel_index: object,
        now_unix: int | None = None,
    ) -> None:
        clean_id = _normalize_node_id_text(subscriber_id)
        if not _is_canonical_node_id(clean_id):
            return
        seen_unix = max(0, int(self._now_unix_fn() if now_unix is None else now_unix))
        normalized_channel = _normalize_channel_index(channel_index)
        with self._lock:
            self._subscribers_by_id[clean_id] = {
                "channel_index": normalized_channel,
                "last_seen_unix": seen_unix,
            }
            if len(self._subscribers_by_id) > _BBS_MAX_SUBSCRIBERS:
                ordered = sorted(
                    self._subscribers_by_id.items(),
                    key=lambda item: int(item[1].get("last_seen_unix") or 0),
                )
                while len(ordered) > _BBS_MAX_SUBSCRIBERS:
                    stale_id, _ = ordered.pop(0)
                    self._subscribers_by_id.pop(stale_id, None)

    def _active_subscribers(self, *, now_unix: int | None = None) -> list[tuple[str, int]]:
        seen_unix = max(0, int(self._now_unix_fn() if now_unix is None else now_unix))
        min_seen = seen_unix - self._subscriber_ttl_seconds
        with self._lock:
            stale_ids = [
                node_id
                for node_id, meta in self._subscribers_by_id.items()
                if int(meta.get("last_seen_unix") or 0) < min_seen
            ]
            for node_id in stale_ids:
                self._subscribers_by_id.pop(node_id, None)
            return [
                (
                    node_id,
                    _normalize_channel_index(meta.get("channel_index")),
                )
                for node_id, meta in self._subscribers_by_id.items()
            ]

    def get_runtime(self) -> dict[str, object]:
        return {
            "ok": True,
            "host": self._status_payload(),
            "posts": self._load_posts(),
        }

    def start(self, request: object | None = None) -> dict[str, object]:
        if request is not None:
            self._save_settings(request)
        local_id = _normalize_node_id_text(self._local_node_id_fn())
        if not _is_canonical_node_id(local_id):
            return {
                "ok": False,
                "error": "Local node ID is unavailable. Wait for sync and try again.",
            }
        next_channel = _normalize_channel_index(
            getattr(request, "channel_index", None),
            fallback=self._status_payload().get("channel_index", 0),
        )
        now_unix = int(self._now_unix_fn())
        with self._lock:
            if not self._enabled or self._started_unix <= 0:
                self._started_unix = now_unix
            self._enabled = True
            self._channel_index = next_channel
        response = self.get_runtime()
        response["message"] = "BBS host is online."
        return response

    def stop(self) -> dict[str, object]:
        with self._lock:
            self._enabled = False
            self._started_unix = 0
            self._subscribers_by_id = {}
        response = self.get_runtime()
        response["message"] = "BBS host is offline."
        return response

    def append_post(self, request: object) -> dict[str, object]:
        with self._lock:
            enabled = bool(self._enabled)
        if not enabled:
            return {
                "ok": False,
                "error": "BBS host is offline.",
            }
        local_id = _normalize_node_id_text(self._local_node_id_fn())
        if not _is_canonical_node_id(local_id):
            return {
                "ok": False,
                "error": "Local node ID is unavailable. Wait for sync and try again.",
            }
        now_unix = int(self._now_unix_fn())
        post = _normalize_post_payload(
            {
                "entry_id": getattr(request, "entry_id", None),
                "author_id": local_id,
                "author_name": getattr(request, "author_name", None),
                "text": getattr(request, "text", None),
                "unix": now_unix,
            }
        )
        if post is None:
            return {
                "ok": False,
                "error": "BBS post text is required.",
            }
        appended = self._append_post(post)
        self._fanout_post(appended)
        response = self.get_runtime()
        response["post"] = appended
        response["message"] = "BBS post saved."
        return response

    def _send_protocol_message_now(
        self,
        *,
        message_type: str,
        fields: list[object],
        destination: str,
        channel_index: int,
    ) -> str:
        payload = _encode_protocol_message(message_type, *fields)
        if not payload:
            return "invalid"
        last_outcome = "send_error"
        for attempt in range(self._max_send_attempts):
            if attempt > 0 and self._retry_backoff_seconds > 0:
                time.sleep(self._retry_backoff_seconds)
            try:
                response = self._send_chat_fn(
                    text=payload,
                    destination=destination,
                    channel_index=channel_index,
                )
            except Exception:
                last_outcome = "send_error"
                continue
            if isinstance(response, Mapping) and response.get("ok") is False:
                last_outcome = str(response.get("error") or "send_error")
                continue
            message_id = None
            if isinstance(response, Mapping):
                message_id = response.get("message_id", response.get("messageId"))
            last_outcome = self._wait_for_delivery_settle(message_id)
            if last_outcome in ("sent", "acked", "received", "delivered", "complete", "completed"):
                return last_outcome
        return last_outcome

    def _wait_for_delivery_settle(self, message_id: object) -> str:
        getter = self._get_delivery_state_fn
        clean_message_id = _to_int(message_id)
        if not callable(getter) or clean_message_id is None or clean_message_id <= 0:
            return "sent"
        timeout_seconds = float(self._delivery_wait_timeout_seconds)
        if timeout_seconds <= 0:
            return "sent"
        deadline = time.monotonic() + timeout_seconds
        final_states = {
            "acked",
            "received",
            "delivered",
            "complete",
            "completed",
            "timeout",
            "failed",
            "error",
            "expired",
            "rejected",
            "declined",
            "cancelled",
            "canceled",
        }
        latest_state = ""
        while time.monotonic() < deadline:
            state = ""
            try:
                current = getter(clean_message_id)
            except Exception:
                return latest_state or "send_error"
            if isinstance(current, Mapping):
                state = str(
                    current.get("delivery_state")
                    or current.get("deliveryState")
                    or current.get("state")
                    or ""
                ).strip().lower()
            else:
                state = str(current or "").strip().lower()
            latest_state = state or latest_state
            if state in final_states:
                return state
            time.sleep(self._delivery_poll_seconds)
        return latest_state or "unsettled"

    def _queue_protocol_message(
        self,
        *,
        message_type: str,
        fields: list[object],
        destination: str,
        channel_index: int,
    ) -> None:
        clean_destination = _normalize_node_id_text(destination)
        if not _is_canonical_node_id(clean_destination):
            return
        payload = {
            "message_type": str(message_type or "").strip().lower(),
            "fields": list(fields or []),
            "destination": clean_destination,
            "channel_index": _normalize_channel_index(channel_index),
        }
        if not payload["message_type"]:
            return
        with self._send_cond:
            self._outbound_queue.append(payload)
            self._send_cond.notify_all()

    def _queue_history_snapshot(
        self,
        *,
        destination: str,
        channel_index: int,
        request_token: str,
    ) -> None:
        settings = self._load_settings()
        local_id = _normalize_node_id_text(self._local_node_id_fn())
        if not _is_canonical_node_id(local_id):
            return
        self._queue_protocol_message(
            message_type="profile",
            fields=[
                request_token,
                settings["board_id"],
                local_id,
                settings["title"],
                settings["motd"],
            ],
            destination=destination,
            channel_index=channel_index,
        )
        posts = self._load_posts()
        for post in posts[-_BBS_MAX_POST_HISTORY_REPLY:]:
            self._queue_protocol_message(
                message_type="post",
                fields=[
                    settings["board_id"],
                    local_id,
                    post.get("entry_id"),
                    post.get("author_id"),
                    post.get("author_name"),
                    post.get("text"),
                ],
                destination=destination,
                channel_index=channel_index,
            )

    def _fanout_post(self, post: Mapping[str, object]) -> None:
        settings = self._load_settings()
        local_id = _normalize_node_id_text(self._local_node_id_fn())
        if not _is_canonical_node_id(local_id):
            return
        subscribers = self._active_subscribers()
        if not subscribers:
            return
        fields = [
            settings["board_id"],
            local_id,
            post.get("entry_id"),
            post.get("author_id"),
            post.get("author_name"),
            post.get("text"),
        ]
        for destination, channel_index in subscribers:
            self._queue_protocol_message(
                message_type="post",
                fields=fields,
                destination=destination,
                channel_index=channel_index,
            )

    def _outbound_loop(self) -> None:
        while True:
            with self._send_cond:
                while not self._outbound_shutdown and not self._outbound_queue:
                    self._outbound_sending = False
                    self._send_cond.notify_all()
                    self._send_cond.wait()
                if self._outbound_shutdown:
                    self._outbound_sending = False
                    self._send_cond.notify_all()
                    return
                payload = self._outbound_queue.popleft()
                self._outbound_sending = True
                spacing_seconds = self._send_spacing_seconds
                next_send_monotonic = float(self._outbound_next_send_monotonic)
            if spacing_seconds > 0:
                sleep_seconds = next_send_monotonic - time.monotonic()
                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)
            self._send_protocol_message_now(
                message_type=str(payload.get("message_type") or ""),
                fields=list(payload.get("fields") or []),
                destination=str(payload.get("destination") or ""),
                channel_index=_normalize_channel_index(payload.get("channel_index")),
            )
            with self._send_cond:
                self._outbound_next_send_monotonic = time.monotonic() + max(0.0, spacing_seconds)
                if not self._outbound_queue:
                    self._outbound_sending = False
                self._send_cond.notify_all()

    def wait_for_idle(self, timeout_seconds: float = 1.0) -> bool:
        deadline = time.monotonic() + max(0.01, float(timeout_seconds))
        with self._send_cond:
            while self._outbound_sending or self._outbound_queue:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._send_cond.wait(timeout=remaining)
        return True

    def on_receive(self, packet: object, interface: object | None = None) -> None:
        parsed = _parse_protocol_message(_extract_packet_text(packet))
        if parsed is None:
            return
        message_type, parts = parsed
        if not isinstance(packet, Mapping):
            return
        with self._lock:
            enabled = bool(self._enabled)
            fallback_channel = int(self._channel_index)
        if not enabled:
            return
        local_num = _get_local_node_num(interface) if interface is not None else None
        packet_to = _to_int(packet.get("to"))
        if local_num is None or packet_to is None or packet_to != int(local_num):
            return
        sender_num = _to_int(packet.get("from"))
        if sender_num is None:
            return
        nodes_by_num = getattr(interface, "nodesByNum", None) if interface is not None else None
        sender_user = {}
        if isinstance(nodes_by_num, dict):
            sender_info = nodes_by_num.get(sender_num, {})
            if isinstance(sender_info, Mapping):
                sender_user = sender_info.get("user", {}) if isinstance(sender_info.get("user"), Mapping) else {}
        sender_id = _normalize_node_id_text(sender_user.get("id") if isinstance(sender_user, Mapping) else "")
        if not _is_canonical_node_id(sender_id):
            sender_id = f"!{int(sender_num):08x}"
        local_id = _normalize_node_id_text(self._local_node_id_fn())
        if not _is_canonical_node_id(local_id):
            return
        settings = self._load_settings()
        reply_channel = _normalize_channel_index(packet.get("channel"), fallback=fallback_channel)
        if message_type == "open":
            request_token = _sanitize_bbs_text(parts[2] if len(parts) > 2 else "", 40)
            if not request_token:
                return
            self._remember_subscriber(
                sender_id,
                channel_index=reply_channel,
                now_unix=int(self._now_unix_fn()),
            )
            self._queue_history_snapshot(
                destination=sender_id,
                channel_index=reply_channel,
                request_token=request_token,
            )
            return
        if message_type != "post":
            return
        board_id = _normalize_bbs_board_id(parts[2] if len(parts) > 2 else "")
        host_id = _normalize_node_id_text(parts[3] if len(parts) > 3 else "")
        if not board_id or board_id != str(settings.get("board_id") or ""):
            return
        if host_id != local_id:
            return
        post = _normalize_post_payload(
            {
                "entry_id": parts[4] if len(parts) > 4 else "",
                "author_id": parts[5] if len(parts) > 5 else sender_id,
                "author_name": parts[6] if len(parts) > 6 else sender_id,
                "text": parts[7] if len(parts) > 7 else "",
                "unix": int(self._now_unix_fn()),
            }
        )
        if post is None:
            return
        try:
            appended = self._append_post(post)
        except Exception:
            return
        self._remember_subscriber(
            sender_id,
            channel_index=reply_channel,
            now_unix=int(self._now_unix_fn()),
        )
        self._fanout_post(appended)


def build_bbs_host_service(**kwargs: object) -> BbsHostService:
    return BbsHostService(**kwargs)


__all__ = [
    "BbsHostService",
    "build_bbs_host_service",
]
