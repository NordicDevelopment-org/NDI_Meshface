import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.html_js import build_dashboard_js


def test_dashboard_js_hardens_node_history_render_failures() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert "Node history render failed:" in js
    assert "Unable to render history for" in js
    assert "Signal history is temporarily unavailable for this node." in js
    assert "Timeline unavailable while re-rendering signal history." in js
    assert "Reselect the node to retry." in js


def test_dashboard_js_clamps_settings_field_selection_restore() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert 'const valueLen = String(field.value || "").length;' in js
    assert "Math.max(0, Math.min(valueLen, Math.trunc(focusedFieldState.selectionStart)))" in js
    assert "Math.max(start, Math.min(valueLen, Math.trunc(focusedFieldState.selectionEnd)))" in js
