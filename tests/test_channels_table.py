import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.html_js import build_dashboard_js


def test_disabled_channel_rows_render_as_blank_new_slot_inputs() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert 'const nameValue = draft && typeof draft.name === "string"' in js
    assert ': isDisabledRole' in js
    assert '? ""' in js
    assert '? false' in js
    assert '? "blank = default"' in js
