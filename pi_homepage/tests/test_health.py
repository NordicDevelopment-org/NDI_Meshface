import socket
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from health import (
    STATUS_DOWN,
    STATUS_UNKNOWN,
    STATUS_UP,
    TileHealthMonitor,
    probe_http,
    probe_tcp,
    probe_tile,
)


def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_probe_tcp_reports_up_against_a_listening_socket() -> None:
    port = _free_tcp_port()
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", port))
    listener.listen(1)
    try:
        assert probe_tcp("127.0.0.1", port, timeout=1.0) == STATUS_UP
    finally:
        listener.close()


def test_probe_tcp_reports_down_against_a_closed_port() -> None:
    port = _free_tcp_port()
    assert probe_tcp("127.0.0.1", port, timeout=1.0) == STATUS_DOWN


def test_probe_http_reports_down_against_an_unreachable_host() -> None:
    port = _free_tcp_port()
    assert probe_http(f"http://127.0.0.1:{port}/", timeout=1.0) == STATUS_DOWN


def test_probe_tile_dispatches_by_method_and_handles_missing_fields() -> None:
    assert probe_tile({}) == STATUS_UNKNOWN
    assert probe_tile({"method": "tcp"}) == STATUS_UNKNOWN
    assert probe_tile({"method": "http"}) == STATUS_UNKNOWN
    assert probe_tile({"method": "carrier-pigeon", "host": "127.0.0.1", "port": 80}) == STATUS_UNKNOWN

    port = _free_tcp_port()
    assert probe_tile({"method": "tcp", "host": "127.0.0.1", "port": port, "timeout_s": 1}) == STATUS_DOWN


def test_tile_health_monitor_snapshot_uses_injected_probe_fn() -> None:
    tiles = [
        {"id": "alpha", "health": {"method": "tcp", "host": "127.0.0.1", "port": 1}},
        {"id": "beta", "health": {"method": "tcp", "host": "127.0.0.1", "port": 2}},
    ]
    calls = []

    def fake_probe(spec: dict) -> str:
        calls.append(spec)
        return STATUS_UP

    monitor = TileHealthMonitor(tiles, probe_fn=fake_probe)
    snapshot = monitor.snapshot()

    assert snapshot["alpha"]["status"] == STATUS_UP
    assert snapshot["beta"]["status"] == STATUS_UP
    assert len(calls) == 2


def test_tile_health_monitor_respects_cache_ttl() -> None:
    tiles = [{"id": "alpha", "health": {"method": "tcp", "host": "127.0.0.1", "port": 1}}]
    call_count = {"n": 0}

    def counting_probe(spec: dict) -> str:
        call_count["n"] += 1
        return STATUS_UP

    monitor = TileHealthMonitor(tiles, cache_ttl_seconds=60.0, probe_fn=counting_probe)
    monitor.snapshot()
    monitor.snapshot()
    monitor.snapshot()

    assert call_count["n"] == 1


def test_tile_health_monitor_skips_tiles_without_health_spec() -> None:
    tiles = [{"id": "alpha"}]
    monitor = TileHealthMonitor(tiles, probe_fn=lambda spec: STATUS_UP)
    snapshot = monitor.snapshot()
    assert snapshot["alpha"]["status"] == STATUS_UNKNOWN


def test_tile_health_monitor_background_refresh_updates_snapshot() -> None:
    tiles = [{"id": "alpha", "health": {"method": "tcp", "host": "127.0.0.1", "port": 1}}]
    statuses = iter([STATUS_DOWN, STATUS_UP])
    lock = threading.Lock()

    def flipping_probe(spec: dict) -> str:
        with lock:
            return next(statuses, STATUS_UP)

    monitor = TileHealthMonitor(tiles, cache_ttl_seconds=0.05, probe_fn=flipping_probe)
    try:
        first = monitor.snapshot()["alpha"]["status"]
        monitor.start_background_refresh(interval_seconds=0.02)
        time.sleep(0.2)
        second = monitor.snapshot()["alpha"]["status"]
        assert first == STATUS_DOWN
        assert second == STATUS_UP
    finally:
        monitor.stop()
