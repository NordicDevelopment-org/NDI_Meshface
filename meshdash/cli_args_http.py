import argparse


def add_http_runtime_args(
    parser: argparse.ArgumentParser,
    *,
    default_http_host: str,
    default_http_port: int,
    default_refresh_ms: int,
    default_packet_limit: int,
) -> None:
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
