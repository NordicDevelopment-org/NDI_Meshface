import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeSettingsRequest:
    preset_name: object
    custom_theme: object
    preview_only: bool


def parse_theme_settings_request(raw_body: bytes) -> ThemeSettingsRequest:
    try:
        body = json.loads(raw_body.decode("utf-8"))
    except Exception:
        body = {}
    payload = body if isinstance(body, dict) else {}
    raw_preview = payload.get("preview_only")
    preview_only = False
    if isinstance(raw_preview, bool):
        preview_only = raw_preview
    elif raw_preview is not None:
        preview_only = str(raw_preview).strip().lower() in {"1", "true", "yes", "on"}
    return ThemeSettingsRequest(
        preset_name=payload.get("preset_name"),
        custom_theme=payload.get("custom_theme"),
        preview_only=preview_only,
    )
