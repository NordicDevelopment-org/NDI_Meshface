from meshdash.html_sections import build_html_shell


def test_build_html_shell_injects_style_js_and_header_tokens():
    html = build_html_shell(
        style_css="/* style-css */",
        app_js="// app-js",
        revision_title="rev-title",
        revision_label="Rev: test",
        safety_label="Secrets redacted",
        packet_limit=250,
        history_label="History: on",
        refresh_ms=3000,
    )
    assert "<style>\n/* style-css */\n  </style>" in html
    assert "<script>\n// app-js\n  </script>" in html
    assert 'title="rev-title">Rev: test<' in html
    assert "Packet buffer: 250" in html
    assert "Refresh: 3000 ms" in html
