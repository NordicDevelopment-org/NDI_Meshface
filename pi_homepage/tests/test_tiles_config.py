import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pi_homepage import DEFAULT_TILES_CONFIG, load_tiles

REPO_TILES_CONFIG = Path(__file__).resolve().parents[1] / "config" / "tiles.json"

EXPECTED_TILE_IDS = {"meshyface", "sdr", "nomadnet", "reticulum", "meshchat"}


def test_default_tiles_config_path_points_at_shipped_config() -> None:
    assert Path(DEFAULT_TILES_CONFIG) == REPO_TILES_CONFIG


def test_shipped_tiles_config_is_well_formed_json_with_required_fields() -> None:
    raw = json.loads(REPO_TILES_CONFIG.read_text(encoding="utf-8"))
    tiles = raw["tiles"]

    assert {tile["id"] for tile in tiles} == EXPECTED_TILE_IDS
    for tile in tiles:
        assert tile["name"]
        assert tile["icon"]
        assert tile["url"].startswith("http://") or tile["url"].startswith("https://")
        health = tile["health"]
        assert health["method"] in ("tcp", "http")
        assert health["host"]
        assert health["port"]


def test_load_tiles_reads_shipped_config() -> None:
    tiles = load_tiles(str(REPO_TILES_CONFIG))
    assert {tile["id"] for tile in tiles} == EXPECTED_TILE_IDS


def test_load_tiles_returns_empty_list_for_missing_file(tmp_path) -> None:
    missing_path = tmp_path / "does-not-exist.json"
    assert load_tiles(str(missing_path)) == []


def test_load_tiles_skips_entries_without_an_id(tmp_path) -> None:
    config_path = tmp_path / "tiles.json"
    config_path.write_text(
        json.dumps({"tiles": [{"id": "good", "name": "Good"}, {"name": "No id"}, {}]}),
        encoding="utf-8",
    )

    tiles = load_tiles(str(config_path))
    assert [tile["id"] for tile in tiles] == ["good"]


def test_load_tiles_accepts_a_bare_list_payload(tmp_path) -> None:
    config_path = tmp_path / "tiles.json"
    config_path.write_text(json.dumps([{"id": "solo", "name": "Solo"}]), encoding="utf-8")

    tiles = load_tiles(str(config_path))
    assert [tile["id"] for tile in tiles] == ["solo"]
