import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.html_css import build_dashboard_css
from meshdash.html_sections import build_html_shell


def test_workspace_views_share_map_style_chrome_primitives() -> None:
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

    assert 'id="apps-tabs-bar" class="apps-tabs-bar workspace-chrome-bar workspace-pillbar"' in html
    assert 'class="settings-chrome workspace-chrome-bar"' in html
    assert 'class="settings-toolbar workspace-chrome-row"' in html
    assert 'class="settings-tabbar workspace-pillbar"' in html
    assert 'class="settings-tab-btn workspace-pill-btn is-active"' in html
    assert 'class="btn workspace-action-chip"' in html
    assert 'class="chat-card-head workspace-chrome-bar"' in html
    assert 'class="games-toolbar workspace-chrome-bar"' in html
    assert 'class="games-tab-btn workspace-pill-btn is-active"' in html
    assert 'id="network-map-chrome" class="network-map-chrome"' in html
    assert 'class="network-map-subview-tabs"' in html

    assert ".workspace-chrome-bar {" in css
    assert ".workspace-pillbar {" in css
    assert ".workspace-chrome-row {" in css
    assert ".network-map-subview-tab,\n    .workspace-pill-btn {" in css
    assert ".workspace-action-chip {" in css
    assert ".settings-chrome {" in css
    assert ".chat-card-head.workspace-chrome-bar {" in css
    assert "[data-theme=\"dark\"] .settings-chrome.workspace-chrome-bar," in css
    assert "[data-theme=\"dark\"] .network-map-subview-tab,\n    [data-theme=\"dark\"] .workspace-pill-btn {" in css
