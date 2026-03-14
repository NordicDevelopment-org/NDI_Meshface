from .html_assets import render_asset_template as _render_asset_template_helper

_DASHBOARD_JS_TEMPLATE_PARTS = (
    "dashboard.js.bootstrap.tmpl",
    "dashboard.js.chat.tmpl",
    "dashboard.js.runtime.tmpl",
)


def build_dashboard_js(
    *,
    refresh_ms: int,
    node_history_hours: int,
    node_history_max_points: int,
    reset_ticker_scale_on_restart: bool = True,
) -> str:
    values = {
        "refresh_ms": refresh_ms,
        "node_history_hours": node_history_hours,
        "node_history_max_points": node_history_max_points,
        "reset_ticker_scale_on_restart": (
            1 if bool(reset_ticker_scale_on_restart) else 0
        ),
    }
    return "".join(
        _render_asset_template_helper(template_name, **values)
        for template_name in _DASHBOARD_JS_TEMPLATE_PARTS
    )
