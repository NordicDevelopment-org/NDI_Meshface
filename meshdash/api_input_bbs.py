import json
from dataclasses import dataclass


@dataclass(frozen=True)
class BbsSettingsRequest:
    title: object = None
    board_id: object = None
    motd: object = None


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
