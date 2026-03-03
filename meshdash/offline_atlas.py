from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any
import json

_ASSETS_DIR = Path(__file__).with_name("assets")
_OFFLINE_ATLAS_PATH = _ASSETS_DIR / "offline_atlas_na.min.json"


@lru_cache(maxsize=1)
def load_offline_atlas_payload() -> dict[str, Any]:
    try:
        text = _OFFLINE_ATLAS_PATH.read_text(encoding="utf-8")
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
    except Exception as exc:
        return {
            "ok": False,
            "error": f"offline atlas unavailable: {exc}",
            "layers": {},
            "counts": {},
        }
    return {
        "ok": False,
        "error": "offline atlas payload invalid",
        "layers": {},
        "counts": {},
    }

