from meshdash.html import render_html


def test_render_html_includes_revision_and_runtime_values():
    html = render_html(
        refresh_ms=3000,
        packet_limit=250,
        show_secrets=False,
        history_enabled=True,
        history_max_rows=5000,
        history_retention_days=7,
        node_history_hours=72,
        node_history_max_points=1440,
        revision_label="Rev: v0.1.0 (abc123)",
        revision_title="v0.1.0 / abc123",
    )
    assert "Meshtastic Dashboard" in html
    assert "Rev: v0.1.0 (abc123)" in html
    assert "History: on (7d retention, 5000 rows max)" in html
    assert "const refreshMs = 3000;" in html
    assert "setInterval(poll, refreshMs);" in html
