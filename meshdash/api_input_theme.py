import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeSettingsRequest:
    preset_name: object


def parse_theme_settings_request(raw_body: bytes) -> ThemeSettingsRequest:
    try:
        body = json.loads(raw_body.decode("utf-8"))
    except Exception:
        body = {}
    payload = body if isinstance(body, dict) else {}
    return ThemeSettingsRequest(preset_name=payload.get("preset_name"))
