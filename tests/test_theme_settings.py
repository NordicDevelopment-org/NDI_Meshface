import json

from meshdash.theme_presets import default_theme_presets
from meshdash.theme_settings import (
    ThemePresetSettings,
    load_selected_theme_preset,
    save_selected_theme_preset,
)


def _preset_map() -> dict[str, dict[str, dict[str, str]]]:
    presets = default_theme_presets()
    light = dict(presets["default"]["light"])
    dark = dict(presets["default"]["dark"])
    light["--accent"] = "#123456"
    dark["--ui-accent"] = "#abcdef"
    presets["forest"] = {"light": light, "dark": dark}
    return presets


def test_load_and_save_selected_theme_preset_roundtrip(tmp_path):
    settings_path = tmp_path / "theme_settings.json"
    assert load_selected_theme_preset(str(settings_path)) is None

    err = save_selected_theme_preset(str(settings_path), "forest")
    assert err is None
    assert load_selected_theme_preset(str(settings_path)) == "forest"


def test_theme_preset_settings_prefers_persisted_selection(tmp_path):
    settings_path = tmp_path / "theme_settings.json"
    settings_path.write_text(json.dumps({"selected_preset": "forest"}), encoding="utf-8")

    settings = ThemePresetSettings(
        presets=_preset_map(),
        selected_preset="default",
        settings_path=str(settings_path),
    )

    assert settings.selected_preset_name() == "forest"
    tokens = settings.selected_preset_tokens()
    assert tokens["light"]["--accent"] == "#123456"
    payload = settings.get_settings_payload()
    assert payload["selected_preset"] == "forest"
    assert "forest" in payload["available_presets"]
    assert "presets" in payload


def test_theme_preset_settings_rejects_unknown_preset(tmp_path):
    settings = ThemePresetSettings(
        presets=_preset_map(),
        selected_preset="default",
        settings_path=str(tmp_path / "theme_settings.json"),
    )

    response = settings.set_selected_preset("missing")
    assert response["ok"] is False
    assert "Unknown theme preset" in str(response["error"])


def test_theme_preset_settings_updates_and_persists_selection(tmp_path):
    settings_path = tmp_path / "theme_settings.json"
    settings = ThemePresetSettings(
        presets=_preset_map(),
        selected_preset="default",
        settings_path=str(settings_path),
    )

    response = settings.set_selected_preset("forest")
    assert response["ok"] is True
    assert response["selected_preset"] == "forest"
    assert load_selected_theme_preset(str(settings_path)) == "forest"
