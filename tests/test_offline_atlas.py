from __future__ import annotations

import json
from pathlib import Path

from meshdash.offline_atlas import load_offline_atlas_payload, nearest_city


ATLAS_PATH = Path(__file__).resolve().parents[1] / "meshdash" / "assets" / "offline_atlas_na.min.json"


def test_offline_atlas_has_global_basemap_inside_size_budget() -> None:
    payload = json.loads(ATLAS_PATH.read_text(encoding="utf-8"))
    counts = payload.get("counts") or {}

    assert ATLAS_PATH.stat().st_size < 5 * 1024 * 1024
    assert payload.get("bbox") == {"west": -180.0, "south": -90.0, "east": 180.0, "north": 90.0}
    assert counts.get("countries", 0) >= 170
    assert counts.get("coastline", 0) >= 100
    assert counts.get("borders", 0) >= 300
    assert counts.get("cities", 0) >= 4200
    assert counts.get("lakes", 0) >= 130
    assert counts.get("rivers", 0) >= 60


def test_nearest_city_uses_global_offline_city_rows() -> None:
    load_offline_atlas_payload.cache_clear()

    london = nearest_city(51.5072, -0.1276)
    tokyo = nearest_city(35.6762, 139.6503)

    assert london is not None
    assert london["name"] == "London"
    assert london["country"] == "United Kingdom"
    assert london["rank"] == 1
    assert tokyo is not None
    assert tokyo["name"] == "Tokyo"
    assert tokyo["country"] == "Japan"
    assert tokyo["rank"] == 0
