import argparse


def add_default_gateway_args(
    parser: argparse.ArgumentParser,
    *,
    resolved_gateway_host: str,
    resolved_gateway_port: int,
) -> None:
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
