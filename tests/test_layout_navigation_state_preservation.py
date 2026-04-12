import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.html_js import build_dashboard_js


def test_dashboard_js_keeps_layout_switches_in_app() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )
    start = js.index("function meshSelectLayoutView(viewName)")
    end = js.index("// Expose view switching globally", start)
    switcher_block = js[start:end]

    assert "function meshSelectLayoutView(viewName)" in js
    assert "Never hard-reload the page on a view switch miss." in switcher_block
    assert "window.location.reload()" not in switcher_block
    assert "window.requestAnimationFrame(() => {" in switcher_block


def test_dashboard_js_limits_apps_view_to_games_and_files() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert 'if (clean === "games") {' in js
    assert 'return clean === "games" || (clean === "files" && fileTransferFeatureEnabled);' in js
    assert '|| resolved === "bbs"' not in js
    assert '"bbs"' not in js.split("const knownLayoutViews = new Set([", 1)[1].split("]);", 1)[0]
    assert '"bots"' not in js.split("const knownLayoutViews = new Set([", 1)[1].split("]);", 1)[0]


def test_dashboard_js_keeps_whois_quick_action_boot_helpers() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert "function normalizeWhoisCommandPrefix(value)" in js
    assert "function nodeIdSuffixForWhois(nodeId)" in js
    assert "function buildWhoisCommandForNode(nodeId, prefixValue = chatWhoisQuickActionPrefix)" in js
    assert "function loadChatWhoisQuickActionConfig()" in js
    assert "function bindChatWhoisQuickActionControls()" in js


def test_dashboard_js_binds_games_picker_select() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert 'const gamesLibrarySelect = document.getElementById("games-library-select");' in js
    assert 'if (gamesLibrarySelect instanceof HTMLSelectElement) {' in js
    assert 'gamesLibrarySelect.value = activeGameId;' in js
    assert 'gamesLibrarySelect.addEventListener("change", () => {' in js
    assert 'activeGameId = normalizeActiveGameId(gamesLibrarySelect.value);' in js


def test_dashboard_js_limits_app_channel_routing_to_games() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    start = js.index("function meshChannelAppRoutingRows() {")
    end = js.index("function normalizeMeshChannelAppId", start)
    routing_block = js[start:end]

    assert 'id: "games"' in routing_block
    assert 'label: "Games"' in routing_block
    assert 'id: "bbs"' not in routing_block
    assert 'label: "BBS"' not in routing_block
