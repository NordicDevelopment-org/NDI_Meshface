import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ZorkBotToggleRequest:
    enabled: bool | None
    action: str = ""
    peer_id: object = None


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
    has_enabled = "enabled" in payload
    enabled = _parse_enabled(payload.get("enabled")) if has_enabled else None
    action = str(payload.get("action") or "").strip().lower().replace("-", "_")
    if not action and has_enabled:
        action = "enable" if enabled else "disable"
    return ZorkBotToggleRequest(
        enabled=enabled,
        action=action,
        peer_id=payload.get("peer_id", payload.get("peerId")),
    )


__all__ = ["ZorkBotToggleRequest", "parse_zork_bot_toggle_request"]
