import re
from pathlib import Path

from meshdash.html_assets import render_asset_template


_ASSETS_DIR = Path(__file__).resolve().parents[1] / "meshdash" / "assets"
_SINGLE_TEMPLATE_TOKEN_RE = re.compile(r"(?<![${])\{([a-z_][a-z0-9_]*)\}")

_EXPECTED_TEMPLATE_TOKENS = {
    "dashboard.css.tmpl": {"theme_css"},
    "dashboard.js.tmpl": {
        "refresh_ms",
        "node_history_hours",
        "node_history_max_points",
    },
    "dashboard.html.tmpl": {
        "style_css",
        "app_js",
        "revision_title",
        "revision_label",
        "safety_label",
        "packet_limit",
        "history_label",
        "refresh_ms",
    },
}


def _template_tokens(template_name: str) -> set[str]:
    raw = (_ASSETS_DIR / template_name).read_text(encoding="utf-8")
    return set(_SINGLE_TEMPLATE_TOKEN_RE.findall(raw))


def test_asset_templates_expose_only_expected_tokens():
    for template_name, expected_tokens in _EXPECTED_TEMPLATE_TOKENS.items():
        assert _template_tokens(template_name) == expected_tokens


def test_rendered_asset_templates_leave_no_single_token_placeholders():
    render_values = {
        "dashboard.css.tmpl": {
            "theme_css": ":root { --unit-test-token: #123456; }",
        },
        "dashboard.js.tmpl": {
            "refresh_ms": 3000,
            "node_history_hours": 72,
            "node_history_max_points": 1440,
        },
        "dashboard.html.tmpl": {
            "style_css": "/* css */",
            "app_js": "// js",
            "revision_title": "Rev title",
            "revision_label": "Rev label",
            "safety_label": "Secrets redacted",
            "packet_limit": 250,
            "history_label": "History: on",
            "refresh_ms": 3000,
        },
    }

    for template_name, values in render_values.items():
        rendered = render_asset_template(template_name, **values)
        for token in _EXPECTED_TEMPLATE_TOKENS[template_name]:
            assert f"{{{token}}}" not in rendered
