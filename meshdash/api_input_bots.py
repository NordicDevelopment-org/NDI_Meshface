import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ZorkBotToggleRequest:
    enabled: bool


def _parse_enabled(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        raise ValueError("enabled is required")
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "on", "enable", "enabled"}:
        return True
    if text in {"0", "false", "no", "off", "disable", "disabled"}:
        return False
    raise ValueError("enabled must be boolean")


def parse_zork_bot_toggle_request(raw_body: bytes) -> ZorkBotToggleRequest:
    try:
        body = json.loads(raw_body.decode("utf-8"))
    except Exception:
        body = {}
    payload = body if isinstance(body, dict) else {}
    settings = payload.get("settings")
    if isinstance(settings, dict):
        payload = settings
    return ZorkBotToggleRequest(enabled=_parse_enabled(payload.get("enabled")))


__all__ = ["ZorkBotToggleRequest", "parse_zork_bot_toggle_request"]
