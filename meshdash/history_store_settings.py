import json
import re
import time

from .history_env_metrics import (
    normalize_custom_telemetry_rules as _normalize_custom_telemetry_rules,
)
from .history_store_runtime_contracts import HistoryStoreReadState, HistoryStoreWriteState

_CUSTOM_TELEMETRY_RULES_KEY = "custom_telemetry_rules_v1"
_BBS_HOST_SETTINGS_KEY = "bbs_host_settings_v1"


def _sanitize_bbs_text(value: object, max_chars: int) -> str:
    limit = max(1, int(max_chars))
    return (
        " ".join(str(value if value is not None else "").replace("|", " ").split())
        .strip()
        [:limit]
    )


def _normalize_bbs_board_id(value: object, fallback: object = "") -> str:
    text = str(value or fallback or "").strip().lower()
    text = re.sub(r"[^a-z0-9_-]+", "-", text)
    text = re.sub(r"-+", "-", text)
    text = re.sub(r"^[-_]+|[-_]+$", "", text)
    return text[:24]


def _normalize_bbs_host_settings(payload: object) -> dict[str, object]:
    source = payload if isinstance(payload, dict) else {}
    title = _sanitize_bbs_text(source.get("title"), 42) or "Packet Exchange"
    board_id = _normalize_bbs_board_id(
        source.get("board_id", source.get("boardId")),
        title,
    )
    motd = _sanitize_bbs_text(source.get("motd"), 120) or "2400 baud online."
    return {
        "title": title,
        "board_id": board_id,
        "motd": motd,
    }


def _load_custom_telemetry_rules_unlocked(
    store: HistoryStoreReadState,
) -> tuple[list[dict[str, object]], int]:
    row = store._conn.execute(
        """
        SELECT value_json, updated_unix
        FROM dashboard_settings
        WHERE key = ?
        """,
        (_CUSTOM_TELEMETRY_RULES_KEY,),
    ).fetchone()
    if not row:
        return [], 0
    value_json = row[0] if len(row) > 0 else "[]"
    updated_unix = int(row[1] if len(row) > 1 and row[1] is not None else 0)
    try:
        parsed = json.loads(str(value_json or "[]"))
    except Exception:
        parsed = []
    rules = _normalize_custom_telemetry_rules(parsed)
    return rules, updated_unix


def load_custom_telemetry_settings(
    store: HistoryStoreReadState,
) -> dict[str, object]:
    with store._lock:
        rules, updated_unix = _load_custom_telemetry_rules_unlocked(store)
        setattr(store, "_custom_telemetry_rules", list(rules))
        setattr(store, "_custom_telemetry_updated_unix", int(updated_unix))
    return {
        "ok": True,
        "rules": rules,
        "updated_unix": int(updated_unix),
    }


def load_bbs_settings(
    store: HistoryStoreReadState,
) -> dict[str, object]:
    default_settings = _normalize_bbs_host_settings({})
    with store._lock:
        row = store._conn.execute(
            """
            SELECT value_json, updated_unix
            FROM dashboard_settings
            WHERE key = ?
            """,
            (_BBS_HOST_SETTINGS_KEY,),
        ).fetchone()
        if not row:
            settings = default_settings
            updated_unix = 0
        else:
            value_json = row[0] if len(row) > 0 else "{}"
            updated_unix = int(row[1] if len(row) > 1 and row[1] is not None else 0)
            try:
                parsed = json.loads(str(value_json or "{}"))
            except Exception:
                parsed = {}
            settings = _normalize_bbs_host_settings(parsed)
        setattr(store, "_bbs_host_settings", dict(settings))
        setattr(store, "_bbs_host_settings_updated_unix", int(updated_unix))
    return {
        "ok": True,
        "settings": settings,
        "updated_unix": int(updated_unix),
    }


def save_custom_telemetry_settings(
    store: HistoryStoreWriteState,
    *,
    rules: object,
) -> dict[str, object]:
    payload = rules
    if isinstance(payload, dict) and "rules" in payload:
        payload = payload.get("rules")
    if payload is None:
        raise ValueError("Custom telemetry rules payload is required")
    if not isinstance(payload, list):
        raise ValueError("Custom telemetry rules must be a JSON array")

    normalized_rules = _normalize_custom_telemetry_rules(payload)
    updated_unix = int(time.time())
    value_json = json.dumps(normalized_rules, separators=(",", ":"))
    with store._lock:
        store._conn.execute(
            """
            INSERT INTO dashboard_settings(key, value_json, updated_unix)
            VALUES(?, ?, ?)
            ON CONFLICT(key) DO UPDATE
            SET value_json = excluded.value_json,
                updated_unix = excluded.updated_unix
            """,
            (_CUSTOM_TELEMETRY_RULES_KEY, value_json, updated_unix),
        )
        setattr(store, "_custom_telemetry_rules", list(normalized_rules))
        setattr(store, "_custom_telemetry_updated_unix", int(updated_unix))
        store._conn.commit()
    return {
        "ok": True,
        "rules": normalized_rules,
        "updated_unix": int(updated_unix),
    }


def save_bbs_settings(
    store: HistoryStoreWriteState,
    *,
    settings: object,
) -> dict[str, object]:
    payload = settings
    if hasattr(payload, "title") or hasattr(payload, "board_id") or hasattr(payload, "motd"):
        payload = {
            "title": getattr(payload, "title", None),
            "board_id": getattr(payload, "board_id", None),
            "motd": getattr(payload, "motd", None),
        }
    if isinstance(payload, dict) and "settings" in payload and isinstance(payload.get("settings"), dict):
        payload = payload.get("settings")
    normalized_settings = _normalize_bbs_host_settings(payload)
    updated_unix = int(time.time())
    value_json = json.dumps(normalized_settings, separators=(",", ":"))
    with store._lock:
        store._conn.execute(
            """
            INSERT INTO dashboard_settings(key, value_json, updated_unix)
            VALUES(?, ?, ?)
            ON CONFLICT(key) DO UPDATE
            SET value_json = excluded.value_json,
                updated_unix = excluded.updated_unix
            """,
            (_BBS_HOST_SETTINGS_KEY, value_json, updated_unix),
        )
        setattr(store, "_bbs_host_settings", dict(normalized_settings))
        setattr(store, "_bbs_host_settings_updated_unix", int(updated_unix))
        store._conn.commit()
    return {
        "ok": True,
        "settings": normalized_settings,
        "updated_unix": int(updated_unix),
    }
