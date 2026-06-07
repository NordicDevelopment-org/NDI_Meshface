import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.html_js import build_dashboard_js
from meshdash.html_template import render_html
from meshdash.http_routes_get import _APP_ASSETS


def test_render_html_includes_reset_all_local_settings_button() -> None:
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

    assert 'id="settings-reset-local-state"' in html
    assert "Reset All Local Settings" in html
    assert "browser-local reset clears this dashboard origin" in html


def test_render_html_includes_keep_screen_on_setting() -> None:
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

    assert 'id="settings-appearance-keep-screen-on"' in html
    assert "Keep screen on while dashboard is open" in html
    assert 'id="settings-wake-lock-status"' in html


def test_dashboard_js_includes_browser_local_reset_flow() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert 'const resetLocalStateBtn = document.getElementById("settings-reset-local-state");' in js
    assert 'void resetAllLocalSettings();' in js
    assert "async function resetAllLocalSettings()" in js
    assert "window.localStorage.clear();" in js
    assert "window.sessionStorage.clear();" in js
    assert "await clearOriginCacheStorage();" in js
    assert "await clearOriginIndexedDbStorage();" in js
    assert 'window.location.reload();' in js
    assert '"Type RESET LOCAL to clear browser-local dashboard settings and reload:"' in js


def test_dashboard_js_includes_screen_wake_lock_flow() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert 'const settingsScreenWakeLockStorageKey = "meshDashboardSettingsScreenWakeLockV1";' in js
    assert 'const screenWakeLockFallbackVideoUrl = "/assets/screen-wake-fallback.webm";' in js
    assert 'const screenWakeLockFallbackMp4Url = "/assets/screen-wake-fallback.mp4";' in js
    assert "let settingsScreenWakeLockEnabled = true;" in js
    assert "function initializeScreenWakeLock()" in js
    assert "function acquireScreenWakeLockFallback()" in js
    assert 'navigator.wakeLock.request("screen")' in js
    assert "video.play()" in js
    assert 'document.addEventListener("visibilitychange"' in js
    assert 'window.addEventListener("pagehide"' in js
    assert 'for (const eventName of ["pointerdown", "touchstart", "mousedown", "keydown"])' in js
    assert "requestScreenWakeLockFromUserGesture();" in js
    assert "hasActiveFileTransferSessions()" in js
    assert 'controlId === "settings-appearance-keep-screen-on"' in js
    assert 'runBootStep("initializeScreenWakeLock", () => initializeScreenWakeLock());' in js


def test_screen_wake_fallback_media_assets_are_whitelisted() -> None:
    webm = Path("meshdash/assets/screen-wake-fallback.webm")
    mp4 = Path("meshdash/assets/screen-wake-fallback.mp4")

    assert _APP_ASSETS["/assets/screen-wake-fallback.webm"] == (
        "screen-wake-fallback.webm",
        "video/webm",
    )
    assert _APP_ASSETS["/assets/screen-wake-fallback.mp4"] == (
        "screen-wake-fallback.mp4",
        "video/mp4",
    )
    assert webm.read_bytes().startswith(b"\x1a\x45\xdf\xa3")
    assert b"ftyp" in mp4.read_bytes()[:32]
