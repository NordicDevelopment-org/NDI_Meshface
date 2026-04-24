import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.cli import build_dashboard_parser
from meshdash.html_template import render_html


def test_render_html_hides_bbs_workspace_by_default() -> None:
    html = render_html(
        refresh_ms=1000,
        packet_limit=200,
        show_secrets=False,
        history_enabled=True,
        history_max_rows=200,
        history_retention_days=7,
        node_history_hours=24,
        node_history_max_points=240,
        revision_label="test",
        revision_title="test",
    )

    assert 'const bbsFeatureEnabled = !!Number(0);' in html
    assert re_search(
        html,
        r'<button[\s\S]*data-app-view="bbs"[\s\S]*hidden disabled aria-hidden="true"'
    )
    assert '<section class="card bbs" aria-label="BBS" hidden aria-hidden="true">' in html


def test_render_html_shows_bbs_workspace_when_enabled() -> None:
    html = render_html(
        refresh_ms=1000,
        packet_limit=200,
        show_secrets=False,
        history_enabled=True,
        history_max_rows=200,
        history_retention_days=7,
        node_history_hours=24,
        node_history_max_points=240,
        revision_label="test",
        revision_title="test",
        bbs_enabled=True,
    )

    assert 'const bbsFeatureEnabled = !!Number(1);' in html
    assert 'data-app-view="bbs"' in html
    assert '<section class="card bbs" aria-label="BBS">' in html
    assert 'id="bbs-host-title-input"' in html
    assert 'id="bbs-terminal-log"' in html
    assert 'Open Selected' in html
    assert 'id="bbs-host-announce-btn"' not in html


def test_dashboard_parser_supports_bbs_enable_flag_and_env_default() -> None:
    parser = build_dashboard_parser(
        add_mesh_connection_args_fn=_add_mesh_connection_args,
        default_mesh_port="/dev/ttyUSB0",
        default_gateway_host="",
        default_gateway_port=4403,
        env_gateway_host="",
        env_gateway_port=None,
        default_http_host="127.0.0.1",
        default_http_port=8877,
        default_refresh_ms=3000,
        default_packet_limit=250,
        default_reset_ticker_scale_on_restart=True,
        default_history_db="mesh_dashboard_history.sqlite3",
        env_history_db=None,
        default_history_max_rows=1000,
        default_history_retention_days=7,
        default_history_event_max_rows=1000,
        default_history_event_retention_days=30,
        default_history_rollup_retention_days=365,
        default_node_history_hours=72,
        default_node_history_max_points=1440,
        env_theme_presets=None,
        env_theme_preset=None,
        env_theme_settings_file=None,
        default_bbs_enable=False,
        env_bbs_enable="1",
        default_file_transfer_enable=False,
        default_file_transfer_max_bytes=64 * 1024,
        env_file_transfer_enable=None,
        env_file_transfer_max_bytes=None,
        env_accept_file_transfer_traffic_disclaimer=None,
    )

    env_default_args = parser.parse_args([])
    assert env_default_args.bbs_enable is True

    explicit_disable_args = parser.parse_args(["--no-bbs-enable"])
    assert explicit_disable_args.bbs_enable is False

    explicit_enable_args = parser.parse_args(["--bbs-enable"])
    assert explicit_enable_args.bbs_enable is True


def _add_mesh_connection_args(
    parser: argparse.ArgumentParser,
    *,
    default_mesh_port: str,
) -> None:
    parser.add_argument("--mesh-port", default=default_mesh_port)


def re_search(text: str, pattern: str) -> bool:
    import re

    return re.search(pattern, text) is not None
