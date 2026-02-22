from meshdash.cli import build_dashboard_parser, resolve_default_gateway_port


def _fake_add_mesh_connection_args(parser, default_mesh_port):
    parser.add_argument("--mesh-port", default=default_mesh_port)
    parser.add_argument("--mesh-host")
    parser.add_argument("--mesh-tcp-port", type=int, default=4403)


def _build_parser(env_gateway_port=None, env_history_db=None):
    return build_dashboard_parser(
        add_mesh_connection_args_fn=_fake_add_mesh_connection_args,
        default_mesh_port="/dev/ttyACM0",
        default_gateway_host="192.168.1.241",
        default_gateway_port=4403,
        env_gateway_host="10.0.0.5",
        env_gateway_port=env_gateway_port,
        default_http_host="0.0.0.0",
        default_http_port=8877,
        default_refresh_ms=3000,
        default_packet_limit=250,
        default_history_db="mesh_dashboard_history.sqlite3",
        env_history_db=env_history_db,
        default_history_max_rows=5000,
        default_history_retention_days=7,
        default_history_event_max_rows=200000,
        default_history_event_retention_days=30,
        default_history_rollup_retention_days=365,
        default_node_history_hours=72,
        default_node_history_max_points=1440,
    )


def test_resolve_default_gateway_port():
    assert resolve_default_gateway_port("4404", 4403) == 4404
    assert resolve_default_gateway_port(None, 4403) == 4403
    assert resolve_default_gateway_port("not-int", 4403) == 4403


def test_build_dashboard_parser_uses_env_defaults():
    parser = _build_parser(env_gateway_port="5500", env_history_db="/tmp/custom.sqlite3")
    args = parser.parse_args([])
    assert args.default_gateway_host == "10.0.0.5"
    assert args.default_gateway_port == 5500
    assert args.history_db == "/tmp/custom.sqlite3"
    assert args.http_port == 8877
    assert args.node_history_hours == 72
    assert args.node_history_max_points == 1440


def test_build_dashboard_parser_falls_back_on_invalid_gateway_port():
    parser = _build_parser(env_gateway_port="bad-port", env_history_db=None)
    args = parser.parse_args([])
    assert args.default_gateway_port == 4403
    assert args.history_db == "mesh_dashboard_history.sqlite3"
