import socket
from typing import Any, Optional


def guess_lan_ipv4(socket_module: Any = socket) -> Optional[str]:
    try:
        with socket_module.socket(socket_module.AF_INET, socket_module.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass

    try:
        addr_info = socket_module.getaddrinfo(socket_module.gethostname(), None, family=socket_module.AF_INET)
        for _family, _type, _proto, _canonname, sockaddr in addr_info:
            ip = sockaddr[0]
            if ip and not ip.startswith("127."):
                return ip
    except socket_module.gaierror:
        pass

    return None


def apply_default_gateway(args: Any, *, default_mesh_port: str) -> None:
    # If user did not provide --mesh-host and left serial at the default path,
    # prefer the shared TCP gateway for this dashboard.
    if args.no_default_gateway:
        return
    if args.mesh_host:
        return
    if args.mesh_port != default_mesh_port:
        return
    if not args.default_gateway_host:
        return
    args.mesh_host = args.default_gateway_host
    args.mesh_tcp_port = args.default_gateway_port
