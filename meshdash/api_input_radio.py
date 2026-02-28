import json
from dataclasses import dataclass


@dataclass(frozen=True)
class RadioSettingsRequest:
    """A request to apply radio settings to the connected node.

    We support optional LoRa updates plus fixed-position controls.
    """

    lora: dict[str, object]
    fixed_position: dict[str, object]
    clear_fixed_position: bool


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        clean = value.strip().lower()
        if clean in {"1", "true", "yes", "y", "on"}:
            return True
        if clean in {"0", "false", "no", "n", "off", ""}:
            return False
    return bool(value)


def _coerce_float(value: object, *, field_name: str) -> float:
    try:
        if isinstance(value, bool):
            raise ValueError
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            return float(value.strip())
        return float(value)  # type: ignore[arg-type]
    except Exception as exc:
        raise ValueError(f"Expected '{field_name}' to be numeric") from exc


def _coerce_int(value: object, *, field_name: str) -> int:
    try:
        if isinstance(value, bool):
            raise ValueError
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            return int(float(value.strip()))
        return int(value)  # type: ignore[arg-type]
    except Exception as exc:
        raise ValueError(f"Expected '{field_name}' to be numeric") from exc


def _parse_fixed_position(value: object) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("Expected 'fixed_position' to be an object")
    if not value:
        return {}

    lat_raw = value.get("latitude")
    if lat_raw is None:
        lat_raw = value.get("lat")
    lon_raw = value.get("longitude")
    if lon_raw is None:
        lon_raw = value.get("lon")
    alt_raw = value.get("altitude")
    if alt_raw is None:
        alt_raw = value.get("alt")

    if lat_raw is None or lon_raw is None:
        raise ValueError("Expected fixed_position to include latitude and longitude")

    lat = _coerce_float(lat_raw, field_name="fixed_position.latitude")
    lon = _coerce_float(lon_raw, field_name="fixed_position.longitude")
    if not (-90.0 <= lat <= 90.0):
        raise ValueError("fixed_position.latitude out of range (-90..90)")
    if not (-180.0 <= lon <= 180.0):
        raise ValueError("fixed_position.longitude out of range (-180..180)")

    fixed: dict[str, object] = {
        "latitude": lat,
        "longitude": lon,
    }
    if alt_raw is not None:
        fixed["altitude"] = _coerce_int(alt_raw, field_name="fixed_position.altitude")
    return fixed


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

    fixed_position = _parse_fixed_position(payload.get("fixed_position"))
    clear_fixed_position = _coerce_bool(payload.get("clear_fixed_position", False))

    return RadioSettingsRequest(
        lora=clean_lora,
        fixed_position=fixed_position,
        clear_fixed_position=clear_fixed_position,
    )
