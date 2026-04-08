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
    assert 'class="topbar-view-menu-btn-label">Views<' in html
    assert 'id="layout-view-menu-head-current"' in html
    assert 'id="layout-view-menu-btn"' in html
    assert 'id="layout-view-menu"' in html
    assert 'data-view="chat"' in html
    assert 'data-view="network"' in html
    assert 'data-view="apps"' in html
    assert '<aside class="teams-rail"' not in html

    assert ".workspace-launcher-row {" in css
    assert ".workspace-launcher-shell {" in css
    assert "min-height: 38px;" in css
    assert ".topbar-view-menu-btn {" in css
    assert ".topbar-view-menu-btn-label {" in css
    assert ".topbar-view-menu-head {" in css
    assert ".topbar-view-menu-item-icon {" in css
    assert ".topbar-view-menu {" in css
    assert re.search(
        r"\.workspace-shell \{\s*--chat-panel-width: 250px;[\s\S]*grid-template-rows: auto minmax\(0, 1fr\);",
        css,
    )
    assert re.search(
        r"\.workspace-shell\.chat-panel-open \{[\s\S]*grid-template-rows: auto minmax\(0, 1fr\);",
        css,
    )

    assert "function syncLayoutViewLauncherButtonState(viewName = activeLayoutView) {" in js
    assert 'target.closest("#layout-view-menu .topbar-view-menu-item")' in js
    assert 'document.getElementById("layout-view-menu-head-current")' in js
    assert 'document.getElementById("layout-view-menu-btn")' in js
    assert 'Math.max(260, Math.ceil(btnRect.width))' in js
    assert 'window.syncLayoutViewLauncherButtonState = syncLayoutViewLauncherButtonState;' in js
