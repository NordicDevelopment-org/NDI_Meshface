import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.html_js import build_dashboard_js
from meshdash.html_template import render_html


def test_render_html_includes_node_visibility_lists_settings_panel() -> None:
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

    assert 'data-settings-tab="lists"' in html
    assert 'data-settings-tab-panel="lists"' in html
    assert 'id="settings-node-visibility-selected"' in html
    assert 'id="settings-lists-node-search-input"' in html
    assert 'id="settings-lists-search-results"' in html
    assert 'id="settings-whitelist-list"' in html
    assert 'id="settings-blacklist-list"' in html


def test_dashboard_js_includes_node_visibility_lists_runtime_and_filtering() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert 'let latestRawState = null;' in js
    assert 'const nodeVisibilityWhitelistStorageKey = "meshDashboardNodeVisibilityWhitelistV1";' in js
    assert 'const nodeVisibilityBlacklistStorageKey = "meshDashboardNodeVisibilityBlacklistV1";' in js
    assert 'function applyNodeVisibilityFiltersToState(rawState)' in js
    assert 'function renderNodeVisibilityListsUi(state = latestRawState || latestState)' in js
    assert 'latestRawState = rawState;' in js
    assert 'const state = applyNodeVisibilityFiltersToState(rawState);' in js
    assert 'renderNodeVisibilityListsUi(latestRawState || latestState || {});' in js
    assert 'includeHiddenNodes: true,' in js
