import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.html_js import build_dashboard_js
from meshdash.html_template import render_html
from meshdash.theme import (
    DARK_THEME_VARS,
    DEV_THEME_BASE_COLOR,
    DEFAULT_THEME_COLOR_DEPTH,
    LIGHT_THEME_VARS,
    build_palette_theme_preset,
)
from meshdash.theme_presets import default_theme_presets
from meshdash.theme_settings import ThemePresetSettings


def test_default_theme_presets_include_blue_generated_palette() -> None:
    presets = default_theme_presets()

    assert "blue" in presets
    assert presets["blue"] == build_palette_theme_preset(
        DEV_THEME_BASE_COLOR,
        color_depth=DEFAULT_THEME_COLOR_DEPTH,
    )
    assert set(presets["blue"]["light"].keys()) == set(LIGHT_THEME_VARS.keys())
    assert set(presets["blue"]["dark"].keys()) == set(DARK_THEME_VARS.keys())
    assert presets["blue"]["dark"]["--workspace-shell-border"] != DARK_THEME_VARS["--workspace-shell-border"]


def test_theme_settings_support_generated_custom_theme_state() -> None:
    settings = ThemePresetSettings(
        presets=default_theme_presets(),
        selected_preset="default",
        settings_path=None,
    )

    response = settings.apply_settings(
        {
            "preset_name": "custom",
            "custom_theme": {
                "base_color": "#1d4ed8",
                "color_depth": 72,
            },
        }
    )

    expected_custom = build_palette_theme_preset("#1d4ed8", color_depth=72)

    assert response["ok"] is True
    assert response["selected_preset"] == "custom"
    assert response["custom_theme"] == {
        "base_color": "#1d4ed8",
        "color_depth": 72,
    }
    assert "custom" in response["available_presets"]
    assert response["presets"]["custom"] == expected_custom
    assert settings.selected_preset_name() == "custom"
    assert settings.selected_preset_tokens() == expected_custom


def test_theme_customization_controls_are_rendered_and_wired() -> None:
    html = render_html(
        refresh_ms=1000,
        packet_limit=200,
        show_secrets=False,
        history_enabled=True,
        history_max_rows=200,
        history_retention_days=7,
        node_history_hours=24,
        node_history_max_points=240,
        revision_label="test",
        revision_title="test",
    )
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert 'id="theme-custom-base-color"' in html
    assert 'id="theme-custom-color-depth"' in html
    assert 'id="theme-custom-color-depth-value"' in html
    assert 'id="settings-appearance-badge-emoji"' in html
    assert "Default is green, blue is the dev preset" in html
    assert "Higher color depth increases tint and gradient presence" in html
    assert "Badge shows in the workspace menu header" in html

    assert 'let themeCustomBaseColor = "#2f855a";' in js
    assert "let themeCustomColorDepth = 58;" in js
    assert 'const settingsBadgeEmojiStorageKey = "meshDashboardSettingsBadgeEmojiV1";' in js
    assert "function formatThemePresetLabel(name) {" in js
    assert 'return "green";' in js
    assert "function normalizeThemeCustomSettings(rawSettings) {" in js
    assert "function normalizeSettingsBadgeEmoji(value) {" in js
    assert "function syncThemeCustomControls() {" in js
    assert "function buildThemeSettingsSavePayload(options = null) {" in js
    assert "custom_theme: {" in js
    assert 'presetName: "custom"' in js
    assert "function bindThemeCustomControls() {" in js
    assert "bindThemeCustomControls();" in js
    assert 'controlId === "settings-appearance-badge-emoji"' in js
    assert 'controlId === "theme-custom-base-color"' in js
    assert 'controlId === "theme-custom-color-depth"' in js
    assert "payload.custom_theme" in js
