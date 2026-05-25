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

    assert 'data-settings-tab="nodes"' in html
    assert 'data-settings-tab-panel="nodes"' in html
    assert 'id="settings-node-tag-presets-manager"' in html
    assert 'id="settings-node-visibility-selected"' in html
    assert 'id="settings-nodes-node-search-input"' in html
    assert 'id="settings-nodes-search-results"' in html
    assert 'id="settings-meshtastic-list"' in html
    assert "<h4>Meshtastic</h4>" in html
    assert "Hardware favorites sync here automatically." in html
    assert 'id="settings-whitelist-list"' in html
    assert "<h4>Frontend Allow-list</h4>" in html
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
    assert 'function renderNodeTagPresetManagerUi(force = false) {' in js
    assert 'function bindNodeTagPresetManagerControls() {' in js
    assert 'host.contains(document.activeElement)' in js
    assert 'latestRawState = rawState;' in js
    assert 'const state = applyNodeVisibilityFiltersToState(rawState);' in js
    assert 'renderNodeVisibilityListsUi(latestRawState || latestState || {});' in js
    assert 'includeHiddenNodes: true,' in js
    assert "function nodeVisibilityWhitelistFilterActive(state = latestRawState || latestState)" in js
    assert "const meshtasticFavoriteIds = meshtasticFavoriteIdsForVisibility(state);" in js
    assert "if (nodeVisibilityWhitelistFilterActive(state)) {" in js
    assert "const meshtasticFavoriteIds = (typeof meshtasticFavoriteNodeIdsFromState === \"function\")" in js
    assert "const nodeIsMeshtasticFavorite = (nodeId) => {" in js
    assert "const renderMeshtasticList = (host, ids, emptyText) => {" in js
    assert 'data-node-visibility-action="remove-meshtastic-favorite"' in js
    assert "action === \"favorite\"" in js
    assert "action === \"unfavorite\"" in js
    assert "MESHTASTIC" in js
