import json
from dataclasses import dataclass


@dataclass(frozen=True)
class BbsSettingsRequest:
    title: object = None
    board_id: object = None
    motd: object = None


@dataclass(frozen=True)
class BbsHostRequest:
    action: str = ""
    channel_index: object = None
    title: object = None
    board_id: object = None
    motd: object = None
    text: object = None
    author_name: object = None
    entry_id: object = None


def parse_bbs_settings_request(raw_body: bytes) -> BbsSettingsRequest:
    try:
        body = json.loads(raw_body.decode("utf-8"))
    except Exception:
        body = {}
    payload = body if isinstance(body, dict) else {}
    settings = payload.get("settings")
    if isinstance(settings, dict):
        payload = settings
    return BbsSettingsRequest(
        title=payload.get("title"),
        board_id=payload.get("board_id", payload.get("boardId")),
        motd=payload.get("motd"),
    )


def parse_bbs_host_request(raw_body: bytes) -> BbsHostRequest:
    try:
        body = json.loads(raw_body.decode("utf-8"))
    except Exception:
        body = {}
    payload = body if isinstance(body, dict) else {}
    settings = payload.get("settings")
    settings_payload = settings if isinstance(settings, dict) else payload
    action = str(payload.get("action") or "").strip().lower()
    return BbsHostRequest(
        action=action,
        channel_index=payload.get("channel_index", payload.get("channelIndex")),
        title=settings_payload.get("title"),
        board_id=settings_payload.get("board_id", settings_payload.get("boardId")),
        motd=settings_payload.get("motd"),
        text=payload.get("text"),
        author_name=payload.get("author_name", payload.get("authorName")),
        entry_id=payload.get("entry_id", payload.get("entryId")),
    )
