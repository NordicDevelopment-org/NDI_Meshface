import argparse
import types

import pytest

import mesh_connection as mc


def _ns(**kwargs):
    defaults = {
        "mesh_host": None,
        "mesh_port": "/dev/ttyACM0",
        "mesh_tcp_port": 4403,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_mesh_target_label_serial_and_tcp():
    assert mc.mesh_target_label(_ns(mesh_port="/dev/ttyUSB0")) == "/dev/ttyUSB0 (serial)"
    assert mc.mesh_target_label(_ns(mesh_host="192.168.1.10", mesh_tcp_port=4404)) == "192.168.1.10:4404 (tcp)"


def test_open_mesh_interface_raises_when_meshtastic_unavailable(monkeypatch):
    monkeypatch.setattr(mc, "_meshtastic_serial_interface", None)
    monkeypatch.setattr(mc, "_meshtastic_tcp_interface", None)
    with pytest.raises(RuntimeError, match="meshtastic Python package is required"):
        mc.open_mesh_interface(_ns(mesh_host="192.168.1.10"))


def test_open_mesh_interface_calls_tcp_interface(monkeypatch):
    called = {}

    class FakeTCP:
        def __init__(self, hostname, portNumber):
            called["hostname"] = hostname
            called["port"] = portNumber

    fake_tcp_module = types.SimpleNamespace(TCPInterface=FakeTCP)
    fake_serial_module = types.SimpleNamespace(SerialInterface=object)
    monkeypatch.setattr(mc, "_meshtastic_tcp_interface", fake_tcp_module)
    monkeypatch.setattr(mc, "_meshtastic_serial_interface", fake_serial_module)

    result = mc.open_mesh_interface(_ns(mesh_host="192.168.1.55", mesh_tcp_port=4405))
    assert isinstance(result, FakeTCP)
    assert called == {"hostname": "192.168.1.55", "port": 4405}


def test_open_mesh_interface_calls_serial_interface(monkeypatch):
    called = {}

    class FakeSerial:
        def __init__(self, devPath):
            called["devPath"] = devPath

    fake_tcp_module = types.SimpleNamespace(TCPInterface=object)
    fake_serial_module = types.SimpleNamespace(SerialInterface=FakeSerial)
    monkeypatch.setattr(mc, "_meshtastic_tcp_interface", fake_tcp_module)
    monkeypatch.setattr(mc, "_meshtastic_serial_interface", fake_serial_module)

    result = mc.open_mesh_interface(_ns(mesh_port="/dev/ttyUSB1"))
    assert isinstance(result, FakeSerial)
    assert called == {"devPath": "/dev/ttyUSB1"}
