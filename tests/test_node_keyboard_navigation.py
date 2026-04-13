import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.html_js import build_dashboard_js


def test_dashboard_js_includes_node_arrow_navigation_binding() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert "function bindNodeDirectionalKeys()" in js
    assert 'if (ev.key !== "ArrowUp" && ev.key !== "ArrowDown") return;' in js
    assert 'runBootStep("bindNodeDirectionalKeys", () => bindNodeDirectionalKeys());' in js


def test_dashboard_js_limits_arrow_navigation_to_visible_node_lists() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert '["#chat-room-list", ".chat-member-item[data-node-id]"]' in js
    assert '["#favorites-list", ".favorite-node-item[data-node-id]"]' in js
    assert '["#nodes-table", "tbody tr.node-selectable[data-node-id]"]' in js
    assert 'target instanceof HTMLInputElement' in js
    assert 'target instanceof HTMLTextAreaElement' in js
    assert 'target instanceof HTMLSelectElement' in js
