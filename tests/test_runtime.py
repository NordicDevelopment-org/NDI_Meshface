import argparse

from meshdash.runtime import apply_default_gateway, guess_lan_ipv4


class _UdpSocket:
    def __init__(self, ip=None, connect_error=False):
        self._ip = ip
        self._connect_error = connect_error

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def connect(self, _addr):
        if self._connect_error:
            raise OSError("no route")

    def getsockname(self):
        return (self._ip, 12345)


class _SocketModule:
    AF_INET = 2
    SOCK_DGRAM = 2
    gaierror = RuntimeError

    def __init__(self, udp_ip=None, connect_error=False, addrinfo_rows=None):
        self._udp_ip = udp_ip
        self._connect_error = connect_error
        self._addrinfo_rows = addrinfo_rows or []

    def socket(self, _family, _socktype):
        return _UdpSocket(ip=self._udp_ip, connect_error=self._connect_error)

    def gethostname(self):
        return "test-host"

    def getaddrinfo(self, _hostname, _service, family=None):
        assert family == self.AF_INET
        return self._addrinfo_rows


def test_guess_lan_ipv4_prefers_udp_probe_ip():
    module = _SocketModule(udp_ip="10.10.1.50")
    assert guess_lan_ipv4(module) == "10.10.1.50"


def test_guess_lan_ipv4_falls_back_to_addrinfo_when_needed():
    module = _SocketModule(
        udp_ip="127.0.0.1",
        addrinfo_rows=[
            (2, 1, 6, "", ("127.0.0.1", 0)),
            (2, 1, 6, "", ("192.168.88.22", 0)),
        ],
    )
    assert guess_lan_ipv4(module) == "192.168.88.22"


def test_guess_lan_ipv4_returns_none_when_no_valid_candidate():
    module = _SocketModule(udp_ip="127.0.0.1", addrinfo_rows=[(2, 1, 6, "", ("127.0.0.1", 0))])
    assert guess_lan_ipv4(module) is None


def test_apply_default_gateway_only_when_conditions_match():
    args = argparse.Namespace(
        no_default_gateway=False,
        mesh_host=None,
        mesh_port="/dev/ttyACM0",
        default_gateway_host="192.168.1.241",
        default_gateway_port=4403,
        mesh_tcp_port=1234,
    )
    apply_default_gateway(args, default_mesh_port="/dev/ttyACM0")
    assert args.mesh_host == "192.168.1.241"
    assert args.mesh_tcp_port == 4403


def test_apply_default_gateway_skips_when_user_already_set_mesh_host():
    args = argparse.Namespace(
        no_default_gateway=False,
        mesh_host="192.168.1.50",
        mesh_port="/dev/ttyACM0",
        default_gateway_host="192.168.1.241",
        default_gateway_port=4403,
        mesh_tcp_port=1234,
    )
    apply_default_gateway(args, default_mesh_port="/dev/ttyACM0")
    assert args.mesh_host == "192.168.1.50"
    assert args.mesh_tcp_port == 1234
