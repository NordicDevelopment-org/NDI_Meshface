import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.html_js import build_dashboard_js


def test_environment_axis_labels_keep_fixed_precision() -> None:
    js = build_dashboard_js(
        refresh_ms=1000,
        node_history_hours=24,
        node_history_max_points=240,
    )

    assert "function envMetricValueText(raw, fallback = \"n/a\") {" in js
    assert "return num.toFixed(decimals);" in js
    assert "return text.replace(/\\.0+$/, \"\").replace(/(\\.\\d*?)0+$/, \"$1\");" not in js
