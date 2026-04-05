import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.html_js import build_dashboard_js


def test_dashboard_js_uses_curated_default_ticker_layout() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert re.search(
        r'const tickerDefaultOrder = \[\s*"target",\s*"node",\s*"known_nodes",\s*"online_nodes",\s*"packets_per_min",\s*"channel_util",\s*"battery",',
        js,
    )
    assert re.search(
        r'for \(const id of \[\s*"target",\s*"node",\s*"known_nodes",\s*"online_nodes",\s*"packets_per_min",\s*"channel_util",\s*"battery",\s*\]\)',
        js,
    )
    assert 'enabled: { ...tickerDefaultEnabled },' in js
    assert "prefs.enabled[id] = !!defaults.enabled[id];" in js
