import json
from dataclasses import dataclass


@dataclass(frozen=True)
class RadioSettingsRequest:
    """A request to apply radio settings to the connected node.

    This is intentionally narrow for now: we accept a single optional "lora" object
    with snake_case protobuf field names (matching the dashboard's state JSON).
    """

    lora: dict[str, object]


def parse_radio_settings_request(raw_body: bytes) -> RadioSettingsRequest:
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Invalid JSON: {exc}")

    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object")

    lora = payload.get("lora")
    if lora is None:
        lora = {}

    if not isinstance(lora, dict):
        raise ValueError("Expected 'lora' to be an object")

    # Keep only JSON-compatible scalar values or simple lists.
    # (We do this as a guardrail — protobuf messages can have complex fields.)
    clean_lora: dict[str, object] = {}
    for key, value in lora.items():
        if not isinstance(key, str):
            continue
        # Allow null/None; caller may strip nulls.
        if value is None:
            clean_lora[key] = None
            continue
        if isinstance(value, (str, int, float, bool)):
            clean_lora[key] = value
            continue
        if isinstance(value, list) and all(
            (v is None) or isinstance(v, (str, int, float, bool)) for v in value
        ):
            clean_lora[key] = value

    return RadioSettingsRequest(lora=clean_lora)
