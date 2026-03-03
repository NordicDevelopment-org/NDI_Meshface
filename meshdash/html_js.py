from .html_assets import render_asset_template as _render_asset_template_helper


def build_dashboard_js(
    *,
    refresh_ms: int,
    node_history_hours: int,
    node_history_max_points: int,
    reset_ticker_scale_on_restart: bool = True,
) -> str:
    return _render_asset_template_helper(
        "dashboard.js.tmpl",
        refresh_ms=refresh_ms,
        node_history_hours=node_history_hours,
        node_history_max_points=node_history_max_points,
        reset_ticker_scale_on_restart=(
            1 if bool(reset_ticker_scale_on_restart) else 0
        ),
    )
