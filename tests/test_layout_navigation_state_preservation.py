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

    assert "function meshSelectLayoutView(viewName)" in js
    assert "Never hard-reload the page on a view switch miss." in js
    assert "window.location.reload()" not in js
    assert "window.requestAnimationFrame(() => {" in js
