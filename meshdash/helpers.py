import json
import os
import shutil
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple


def to_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def format_epoch(epoch_value: Any) -> Optional[str]:
    epoch = to_int(epoch_value)
    if epoch is None or epoch <= 0:
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def safe_json_loads(value: str, default: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def extract_reply_id(decoded: Any) -> Optional[int]:
    if not isinstance(decoded, dict):
        return None
    for key in ("replyId", "reply_id"):
        value = to_int(decoded.get(key))
        if value is not None and value > 0:
            return value
    return None


def extract_emoji_codepoint(decoded: Any) -> Optional[int]:
    if not isinstance(decoded, dict):
        return None
    raw = decoded.get("emoji")
    if raw is None:
        return None

    if isinstance(raw, str):
        clean = raw.strip()
        if not clean:
            return None
        as_int = to_int(clean)
        if as_int is not None:
            return as_int if as_int > 0 else None
        return ord(clean[0])

    as_int = to_int(raw)
    if as_int is None or as_int <= 0:
        return None
    return as_int


def emoji_from_codepoint(codepoint: Optional[int]) -> Optional[str]:
    value = to_int(codepoint)
    if value is None or value <= 0:
        return None
    try:
        return chr(value)
    except (OverflowError, ValueError):
        return None


def normalize_single_emoji(value: Any) -> Tuple[Optional[str], Optional[int]]:
    if value is None:
        return None, None
    text = str(value).strip()
    if not text:
        return None, None

    as_int = to_int(text)
    if as_int is not None and as_int > 0:
        emoji = emoji_from_codepoint(as_int)
        if emoji:
            return emoji, as_int
        return None, None

    codepoint = ord(text[0])
    emoji = emoji_from_codepoint(codepoint)
    if emoji:
        return emoji, codepoint
    return None, None


def calculate_hops(hop_start: Any, hop_limit: Any) -> Optional[int]:
    start = to_int(hop_start)
    limit = to_int(hop_limit)
    if start is None or limit is None:
        return None
    hops = start - limit
    if hops < 0:
        return None
    return hops


def disk_space_info(path: Optional[str]) -> Dict[str, Any]:
    probe = os.path.abspath(os.path.expanduser(path or "."))
    if os.path.isfile(probe):
        probe = os.path.dirname(probe) or "."
    try:
        usage = shutil.disk_usage(probe)
        total = int(usage.total)
        free = int(usage.free)
        used = int(usage.used)
        free_pct = round((free / total) * 100.0, 1) if total > 0 else None
        used_pct = round((used / total) * 100.0, 1) if total > 0 else None
        return {
            "path": probe,
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "free_pct": free_pct,
            "used_pct": used_pct,
        }
    except Exception as exc:
        return {"path": probe, "error": str(exc)}

