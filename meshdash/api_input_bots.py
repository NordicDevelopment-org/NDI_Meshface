import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ZorkBotToggleRequest:
    enabled: bool | None
    action: str = ""
    command: str = ""
    message_only: bool | None = None
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


def _parse_optional_bool(value: object, *, label: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "on", "enable", "enabled"}:
        return True
    if text in {"0", "false", "no", "off", "disable", "disabled"}:
        return False
    raise ValueError(f"{label} must be boolean")


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
    command = str(payload.get("command") or "").strip().lower().replace("-", "_")
    has_message_only = "message_only" in payload or "messageOnly" in payload
    message_only = _parse_optional_bool(
        payload.get("message_only", payload.get("messageOnly")),
        label="message_only",
    ) if has_message_only else None
    if not action and has_enabled:
        action = "enable" if enabled else "disable"
    return ZorkBotToggleRequest(
        enabled=enabled,
        action=action,
        command=command,
        message_only=message_only,
        peer_id=payload.get("peer_id", payload.get("peerId")),
    )


__all__ = ["ZorkBotToggleRequest", "parse_zork_bot_toggle_request"]
