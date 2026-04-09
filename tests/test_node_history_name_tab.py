import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.html_js import build_dashboard_js
from meshdash.html_template import render_html


def test_render_html_includes_node_history_names_and_overview_tabs() -> None:
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

    assert 'id="tab-btn-names"' in html
    assert 'data-tab="names"' in html
    assert 'id="tab-panel-names"' in html
    assert 'id="node-name-history-host"' in html
    assert 'id="tab-btn-overview"' in html
    assert 'data-tab="overview"' in html
    assert 'id="tab-panel-overview"' in html
    assert 'id="node-history-overview-host"' in html


def test_render_html_places_overview_first_in_history_tabs() -> None:
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

    overview_index = html.index('id="tab-btn-overview"')
    signal_index = html.index('id="tab-btn-signal"')
    packets_index = html.index('id="tab-btn-packets"')
    online_index = html.index('id="tab-btn-online"')
    names_index = html.index('id="tab-btn-names"')

    assert overview_index < signal_index < packets_index < online_index < names_index
    assert 'class="history-tabs workspace-pillbar"' in html
    assert 'class="history-tab-btn workspace-pill-btn is-active" id="tab-btn-overview"' in html
    assert 'id="tab-btn-signal" data-tab="signal" type="button" aria-selected="false"' in html
    assert 'id="tab-panel-overview" class="history-panel"' in html
    assert 'id="tab-panel-signal" class="history-panel" hidden' in html


def test_dashboard_js_renders_name_history_and_overview_under_history_tab() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert 'let activeHistoryTab = "overview";' in js
    assert 'nextTab === "signal" || nextTab === "online" || nextTab === "packets" || nextTab === "names" || nextTab === "overview"' in js
    assert ': "overview";' in js
    assert 'btn.classList.toggle("is-active", isActive);' in js
    assert 'btn.setAttribute("aria-selected", isActive ? "true" : "false");' in js
    assert 'const namesPanel = document.getElementById("tab-panel-names");' in js
    assert 'const overviewPanel = document.getElementById("tab-panel-overview");' in js
    assert 'renderNodeNameHistoryPanel(nameHistoryEntries);' in js
    assert 'renderNodeNameHistoryPanel([], {' in js
    assert 'const nameHistoryEntries = Array.isArray(history && history.name_history)' in js
    assert 'const host = document.getElementById("node-history-overview-host");' in js
    assert 'renderNodeHistoryOverviewPanel(history, {' in js
    assert 'savedNodeHistoryOverviewSectionHtml(history, {' in js
    assert 'const historySection = savedDetailSectionHtml("History",' not in js


def test_render_html_hides_history_caption_inside_drawer_history_view() -> None:
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

    assert '.chat-node-details-history-host #node-history-caption {' in html
    assert 'display: none !important;' in html
