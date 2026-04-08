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
