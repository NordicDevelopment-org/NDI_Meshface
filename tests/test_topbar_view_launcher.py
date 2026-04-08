import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.html_css import build_dashboard_css
from meshdash.html_js import build_dashboard_js
from meshdash.html_sections import build_html_shell


def test_workspace_view_launcher_replaces_legacy_rail_nav() -> None:
    html = build_html_shell(
        app_title="Meshyface",
        app_heading="Meshyface",
        style_css="",
        app_js="",
        revision_title="rev",
        revision_label="rev",
        safety_label="safe",
        packet_limit=100,
        history_label="history",
        refresh_ms=1000,
    )
    css = build_dashboard_css(theme_css="")
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert 'class="workspace-launcher-row"' in html
    assert 'class="workspace-launcher-shell"' in html
    assert 'id="layout-view-menu-btn-label"' in html
    assert 'class="topbar-view-menu-btn-label">Chat<' in html
    assert 'class="topbar-update-ticker workspace-update-ticker"' in html
    assert 'workspace-peer-dm-menu-wrap' in html
    assert 'id="peer-dm-toggle-btn"' in html
    assert 'id="layout-view-menu-head-brand"' in html
    assert 'id="layout-view-menu-head-version"' in html
    assert 'id="layout-view-menu-head-commit"' in html
    assert 'id="layout-view-menu-btn"' in html
    assert 'id="layout-view-menu"' in html
    assert 'id="settings-about-version"' in html
    assert 'id="settings-about-commit"' in html
    assert 'data-view="chat"' in html
    assert 'data-view="network"' in html
    assert 'data-view="apps"' in html
    assert 'id="chat-users-title"' not in html
    assert 'class="topbar-notify-corner"' not in html
    assert 'id="self-radio-profile"' not in html
    assert 'id="chat-change-toggle-btn"' not in html
    assert 'id="revision-text"' not in html
    assert 'class="topbar-main-row"' not in html
    assert 'topbar-view-menu-head-kicker' not in html
    assert 'topbar-view-menu-head-title' not in html
    assert 'layout-view-menu-head-current' not in html
    assert 'class="chat-peer-add-toggle-btn chat-node-navigator-menu-btn chat-users-head-view-btn"' in html
    assert '<aside class="teams-rail"' not in html
    assert re.search(
        r'<div class="workspace-launcher-row"[\s\S]*id="layout-view-menu-btn"[\s\S]*id="topbar-update-ticker"[\s\S]*id="peer-dm-toggle-btn"',
        html,
    )
    assert re.search(
        r'<div class="chat-users-head"[\s\S]*id="chat-node-navigator-menu-btn"[\s\S]*id="chat-peer-add-toggle-btn"',
        html,
    )

    assert ".workspace-launcher-row {" in css
    assert "z-index: 500;" in css
    assert ".workspace-launcher-shell {" in css
    assert ".workspace-peer-dm-menu-wrap {" in css
    assert ".chat-users-head-view-btn {" in css
    assert "min-height: 38px;" in css
    assert ".topbar-update-ticker {" in css
    assert ".workspace-update-ticker {" in css
    assert "flex: 1 1 auto;" in css
    assert "--topbar-corner-reserve: 0px;" in css
    assert "padding-right: var(--topbar-right-inset);" in css
    assert ".topbar-view-menu-btn {" in css
    assert ".topbar-view-menu-btn-label {" in css
    assert ".topbar-view-menu-head {" in css
    assert ".topbar-view-menu-brand {" in css
    assert ".topbar-view-menu-brand-mark {" in css
    assert ".topbar-view-menu-head-brand {" in css
    assert ".topbar-view-menu-head-version," in css
    assert ".topbar-view-menu-head-commit {" in css
    assert ".topbar-view-menu-item-icon {" in css
    assert ".topbar-view-menu {" in css
    assert "z-index: 1350;" in css
    assert ".workspace-peer-dm-menu-wrap .peer-dm-toggle-btn {" in css
    assert "width: 38px;" in css
    assert re.search(
        r"\.workspace-shell \{\s*--chat-panel-width: 250px;[\s\S]*grid-template-rows: auto minmax\(0, 1fr\);",
        css,
    )
    assert re.search(
        r"\.workspace-shell\.chat-panel-open \{[\s\S]*grid-template-rows: auto minmax\(0, 1fr\);",
        css,
    )

    assert "function syncLayoutViewLauncherButtonState(viewName = activeLayoutView) {" in js
    assert "function shouldCloseLayoutViewMenuForScrollTarget(target = null) {" in js
    assert 'document.getElementById("settings-about-version")' in js
    assert 'document.getElementById("settings-about-commit")' in js
    assert 'document.getElementById("layout-view-menu-head-version")' in js
    assert 'document.getElementById("layout-view-menu-head-commit")' in js
    assert 'target.closest("#layout-view-menu .topbar-view-menu-item")' in js
    assert 'document.getElementById("layout-view-menu-btn-label")' in js
    assert 'document.getElementById("layout-view-menu-btn")' in js
    assert 'Math.max(260, Math.ceil(btnRect.width))' in js
    assert 'if (!shouldCloseLayoutViewMenuForScrollTarget(ev ? ev.target : null)) {' in js
    assert 'return target === document.body || target === document.documentElement;' in js
    assert "let topbarCornerReservePx = 0;" in js
    assert 'window.syncLayoutViewLauncherButtonState = syncLayoutViewLauncherButtonState;' in js
