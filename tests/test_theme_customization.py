import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.html_js import build_dashboard_js
from meshdash.html_template import render_html
from meshdash.theme import (
    DARK_THEME_VARS,
    DEFAULT_CUSTOM_THEME_BASE_COLOR,
    DEFAULT_CUSTOM_THEME_COLOR_DEPTH,
    DEFAULT_CUSTOM_THEME_LINE_COLOR,
    DEFAULT_CUSTOM_THEME_TINT_COLOR,
    DEFAULT_CUSTOM_THEME_TINT_INTENSITY,
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
                "line_color": "#ef4444",
                "tint_color": "#64748b",
                "tint_intensity": 61,
                "color_depth": 72,
            },
        }
    )

    expected_custom = build_palette_theme_preset(
        "#1d4ed8",
        line_color="#ef4444",
        tint_color="#64748b",
        tint_intensity=61,
        color_depth=72,
    )
    default_line_custom = build_palette_theme_preset("#1d4ed8", color_depth=72)

    assert response["ok"] is True
    assert response["selected_preset"] == "custom"
    assert response["custom_theme"] == {
        "base_color": "#1d4ed8",
        "line_color": "#ef4444",
        "tint_color": "#64748b",
        "tint_intensity": 61,
        "color_depth": 72,
    }
    assert "custom" in response["available_presets"]
    assert response["presets"]["custom"] == expected_custom
    assert response["presets"]["custom"]["dark"]["--workspace-shell-border"] != default_line_custom["dark"]["--workspace-shell-border"]
    assert settings.selected_preset_name() == "custom"
    assert settings.selected_preset_tokens() == expected_custom


def test_theme_settings_default_to_meshyface_custom_palette() -> None:
    settings = ThemePresetSettings(
        presets=default_theme_presets(),
        selected_preset=None,
        settings_path=None,
    )

    expected_custom = build_palette_theme_preset(
        DEFAULT_CUSTOM_THEME_BASE_COLOR,
        line_color=DEFAULT_CUSTOM_THEME_LINE_COLOR,
        tint_color=DEFAULT_CUSTOM_THEME_TINT_COLOR,
        tint_intensity=DEFAULT_CUSTOM_THEME_TINT_INTENSITY,
        color_depth=DEFAULT_CUSTOM_THEME_COLOR_DEPTH,
    )

    assert settings.selected_preset_name() == "custom"
    assert settings.custom_theme_settings() == {
        "base_color": DEFAULT_CUSTOM_THEME_BASE_COLOR,
        "line_color": DEFAULT_CUSTOM_THEME_LINE_COLOR,
        "tint_color": DEFAULT_CUSTOM_THEME_TINT_COLOR,
        "tint_intensity": DEFAULT_CUSTOM_THEME_TINT_INTENSITY,
        "color_depth": DEFAULT_CUSTOM_THEME_COLOR_DEPTH,
    }
    assert settings.selected_preset_tokens() == expected_custom


def test_theme_settings_preserve_zero_tint_intensity() -> None:
    settings = ThemePresetSettings(
        presets=default_theme_presets(),
        selected_preset="custom",
        settings_path=None,
    )

    response = settings.apply_settings(
        {
            "preset_name": "custom",
            "custom_theme": {
                "base_color": "#1d4ed8",
                "line_color": "#9a9996",
                "tint_color": "#9a9996",
                "tint_intensity": 0,
                "color_depth": 0,
            },
        }
    )

    expected_custom = build_palette_theme_preset(
        "#1d4ed8",
        line_color="#9a9996",
        tint_color="#9a9996",
        tint_intensity=0,
        color_depth=0,
    )

    assert response["ok"] is True
    assert response["custom_theme"]["tint_intensity"] == 0
    assert response["custom_theme"]["color_depth"] == 0
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
    assert 'id="theme-custom-line-color"' in html
    assert 'id="theme-custom-tint-color"' in html
    assert 'id="theme-custom-tint-intensity"' in html
    assert 'id="theme-custom-tint-intensity-value"' in html
    assert 'id="theme-custom-color-depth"' in html
    assert 'id="theme-custom-color-depth-value"' in html
    assert 'id="settings-appearance-badge-emoji"' in html
    assert '<option value="custom">custom</option>' in html
    assert "Fresh installs default to Meshyface blue with a neutral gray line and tint" in html
    assert 'value="#2563eb"' in html
    assert 'value="#9a9996"' in html
    assert 'value="50"' in html
    assert '>50%</output>' in html
    assert "Tint color drives the shared shell tint" in html
    assert "Tint intensity controls how strongly that shared tint shows up" in html
    assert "Badge shows in the workspace menu header" in html

    assert 'let themePresetSelected = "custom";' in js
    assert 'let themeCustomBaseColor = "#2563eb";' in js
    assert 'let themeCustomLineColor = "#9a9996";' in js
    assert 'let themeCustomTintColor = "#9a9996";' in js
    assert "let themeCustomTintIntensity = 50;" in js
    assert "let themeCustomColorDepth = 50;" in js
    assert 'const settingsBadgeEmojiStorageKey = "meshDashboardSettingsBadgeEmojiV1";' in js
    assert "function formatThemePresetLabel(name) {" in js
    assert 'return "green";' in js
    assert "function normalizeThemeCustomSettings(rawSettings) {" in js
    assert "function normalizeThemeCustomLineColor(raw, fallback = \"#9a9996\") {" in js
    assert "function normalizeThemeCustomTintColor(raw, fallback = \"#9a9996\") {" in js
    assert "function normalizeThemeCustomTintIntensity(raw) {" in js
    assert "function normalizeSettingsBadgeEmoji(value) {" in js
    assert "function syncThemeCustomControls() {" in js
    assert "function buildThemeSettingsSavePayload(options = null) {" in js
    assert "custom_theme: {" in js
    assert 'presetName: "custom"' in js
    assert "function bindThemeCustomControls() {" in js
    assert "bindThemeCustomControls();" in js
    assert 'controlId === "settings-appearance-badge-emoji"' in js
    assert 'controlId === "theme-custom-base-color"' in js
    assert 'controlId === "theme-custom-line-color"' in js
    assert 'controlId === "theme-custom-tint-color"' in js
    assert 'controlId === "theme-custom-tint-intensity"' in js
    assert 'controlId === "theme-custom-color-depth"' in js
    assert "payload.custom_theme" in js
