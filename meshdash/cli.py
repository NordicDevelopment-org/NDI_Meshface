import argparse
from typing import Callable, Optional


def resolve_default_gateway_port(raw_value: Optional[str], fallback: int) -> int:
    try:
        return int(raw_value) if raw_value else int(fallback)
    except ValueError:
        return int(fallback)


def build_dashboard_parser(
    *,
    add_mesh_connection_args_fn: Callable[..., None],
    default_mesh_port: str,
    default_gateway_host: str,
    default_gateway_port: int,
    env_gateway_host: str,
    env_gateway_port: Optional[str],
    default_http_host: str,
    default_http_port: int,
    default_refresh_ms: int,
    default_packet_limit: int,
    default_history_db: str,
    env_history_db: Optional[str],
    default_history_max_rows: int,
    default_history_retention_days: int,
    default_history_event_max_rows: int,
    default_history_event_retention_days: int,
    default_history_rollup_retention_days: int,
    default_node_history_hours: int,
    default_node_history_max_points: int,
) -> argparse.ArgumentParser:
    resolved_gateway_port = resolve_default_gateway_port(env_gateway_port, default_gateway_port)
    resolved_gateway_host = str(env_gateway_host or default_gateway_host)
    resolved_history_db = str(env_history_db or default_history_db)

    parser = argparse.ArgumentParser(
        description="Serve a high-detail Meshtastic dashboard with map, node tables, configs, and packet logs."
    )
    add_mesh_connection_args_fn(parser, default_mesh_port=default_mesh_port)
    parser.add_argument(
        "--default-gateway-host",
        default=resolved_gateway_host,
        help=(
            "Fallback TCP host for dashboard mode when --mesh-host is not provided "
            f"(default: {resolved_gateway_host})."
        ),
    )
    parser.add_argument(
        "--default-gateway-port",
        type=int,
        default=resolved_gateway_port,
        help=(
            "Fallback TCP port used with --default-gateway-host when --mesh-host is not provided "
            f"(default: {resolved_gateway_port})."
        ),
    )
    parser.add_argument(
        "--no-default-gateway",
        action="store_true",
        help="Disable default gateway fallback and use serial unless --mesh-host is set.",
    )
    parser.add_argument(
        "--http-host",
        default=default_http_host,
        help=f"HTTP bind host (default: {default_http_host})",
    )
    parser.add_argument(
        "--http-port",
        type=int,
        default=default_http_port,
        help=f"HTTP bind port (default: {default_http_port})",
    )
    parser.add_argument(
        "--refresh-ms",
        type=int,
        default=default_refresh_ms,
        help=f"Browser polling interval in milliseconds (default: {default_refresh_ms})",
    )
    parser.add_argument(
        "--packet-limit",
        type=int,
        default=default_packet_limit,
        help=f"Recent packet history buffer size (default: {default_packet_limit})",
    )
    parser.add_argument(
        "--show-secrets",
        action="store_true",
        help="Display sensitive config values (private keys/passwords/PSKs) in raw JSON panels.",
    )
    parser.add_argument(
        "--history-db",
        default=resolved_history_db,
        help=f"SQLite DB path for persisted chat/packet history and rollups (default: {default_history_db})",
    )
    parser.add_argument(
        "--history-max-rows",
        type=int,
        default=default_history_max_rows,
        help=f"Max persisted rows per history table (default: {default_history_max_rows})",
    )
    parser.add_argument(
        "--history-retention-days",
        type=int,
        default=default_history_retention_days,
        help=(
            "Delete persisted rows older than this many days; "
            f"use 0 to disable age-based pruning (default: {default_history_retention_days})"
        ),
    )
    parser.add_argument(
        "--history-event-max-rows",
        type=int,
        default=default_history_event_max_rows,
        help=(
            "Max rows for append-only packet event history "
            f"(default: {default_history_event_max_rows})"
        ),
    )
    parser.add_argument(
        "--history-event-retention-days",
        type=int,
        default=default_history_event_retention_days,
        help=(
            "Delete packet event rows older than this many days; "
            f"use 0 to disable age-based pruning (default: {default_history_event_retention_days})"
        ),
    )
    parser.add_argument(
        "--history-rollup-retention-days",
        type=int,
        default=default_history_rollup_retention_days,
        help=(
            "Delete rollup rows older than this many days; "
            f"use 0 to disable age-based pruning (default: {default_history_rollup_retention_days})"
        ),
    )
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Disable persisted SQLite history (memory-only live buffers).",
    )
    parser.add_argument(
        "--node-history-hours",
        type=int,
        default=default_node_history_hours,
        help=f"Default selected-node history window in hours (default: {default_node_history_hours})",
    )
    parser.add_argument(
        "--node-history-max-points",
        type=int,
        default=default_node_history_max_points,
        help=(
            "Max selected-node history points returned by /api/history/node "
            f"(default: {default_node_history_max_points})"
        ),
    )
    return parser
