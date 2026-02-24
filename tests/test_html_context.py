from meshdash.html_context import build_html_render_context


def test_build_html_render_context_when_history_enabled():
    context = build_html_render_context(
        show_secrets=False,
        history_enabled=True,
        history_max_rows=5000,
        history_retention_days=7,
    )
    assert context["safety_label"] == "Secrets redacted"
    assert context["history_label"] == "History: on (7d retention, 5000 rows max)"
    assert "--ui-bg" in context["theme_css"]


def test_build_html_render_context_when_history_disabled():
    context = build_html_render_context(
        show_secrets=True,
        history_enabled=False,
        history_max_rows=5000,
        history_retention_days=7,
    )
    assert context["safety_label"] == "Secrets visible"
    assert context["history_label"] == "History: off"


def test_build_html_render_context_accepts_theme_token_overrides():
    context = build_html_render_context(
        show_secrets=False,
        history_enabled=True,
        history_max_rows=100,
        history_retention_days=1,
        light_theme_vars={"--bg": "#ffffff"},
        dark_theme_vars={"--ui-bg": "#000000"},
    )
    assert "--bg: #ffffff;" in context["theme_css"]
    assert "--ui-bg: #000000;" in context["theme_css"]
