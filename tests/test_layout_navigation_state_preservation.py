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


def test_dashboard_js_treats_bbs_as_an_apps_view() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert 'if (clean === "games" || clean === "bbs") {' in js
    assert 'return clean === "games" || clean === "bbs" || (clean === "files" && fileTransferFeatureEnabled);' in js
    assert '|| resolved === "bbs"' in js


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
