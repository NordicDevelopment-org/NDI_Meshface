import logging
import socket
import threading
import time
import urllib.request
from typing import Callable, Optional

logger = logging.getLogger(__name__)

DEFAULT_CACHE_TTL_SECONDS = 8.0
DEFAULT_PROBE_TIMEOUT_SECONDS = 2.0

STATUS_UP = "up"
STATUS_DOWN = "down"
STATUS_UNKNOWN = "unknown"

ProbeFn = Callable[[dict], str]


def probe_tcp(host: str, port: int, *, timeout: float = DEFAULT_PROBE_TIMEOUT_SECONDS) -> str:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return STATUS_UP
    except OSError as exc:
        logger.debug("TCP probe to %s:%s failed: %s", host, port, exc)
        return STATUS_DOWN


def probe_http(url: str, *, timeout: float = DEFAULT_PROBE_TIMEOUT_SECONDS) -> str:
    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (local/LAN tile URLs only)
            return STATUS_UP if response.status < 500 else STATUS_DOWN
    except Exception as exc:
        logger.debug("HTTP probe to %s failed: %s", url, exc)
        return STATUS_DOWN


def probe_tile(health_spec: dict) -> str:
    method = str((health_spec or {}).get("method") or "").strip().lower()
    timeout = float((health_spec or {}).get("timeout_s") or DEFAULT_PROBE_TIMEOUT_SECONDS)
    host = str((health_spec or {}).get("host") or "").strip()
    port = (health_spec or {}).get("port")

    if method == "tcp":
        if not host or not port:
            return STATUS_UNKNOWN
        return probe_tcp(host, int(port), timeout=timeout)

    if method == "http":
        if not host:
            return STATUS_UNKNOWN
        scheme = "https" if str((health_spec or {}).get("scheme") or "").lower() == "https" else "http"
        path = str((health_spec or {}).get("path") or "/")
        port_part = f":{int(port)}" if port else ""
        return probe_http(f"{scheme}://{host}{port_part}{path}", timeout=timeout)

    return STATUS_UNKNOWN


class TileHealthMonitor:
    """Background health-probe cache for launcher tiles.

    Probes are re-run lazily (at most once per `cache_ttl_seconds` per tile)
    either via `start_background_refresh()` or on-demand inside `snapshot()`,
    so a slow/unreachable tile never blocks the HTTP request thread for more
    than one probe's timeout.
    """

    def __init__(
        self,
        tiles: list,
        *,
        cache_ttl_seconds: float = DEFAULT_CACHE_TTL_SECONDS,
        probe_fn: ProbeFn = probe_tile,
    ) -> None:
        self._tiles = list(tiles)
        self._cache_ttl_seconds = float(cache_ttl_seconds)
        self._probe_fn = probe_fn
        self._lock = threading.Lock()
        self._results: dict[str, dict] = {}
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def snapshot(self) -> dict[str, dict]:
        self._refresh_stale()
        with self._lock:
            return {tile_id: dict(result) for tile_id, result in self._results.items()}

    def _refresh_stale(self) -> None:
        now = time.monotonic()
        for tile in self._tiles:
            tile_id = str(tile.get("id") or "")
            if not tile_id:
                continue
            with self._lock:
                cached = self._results.get(tile_id)
            if cached is not None and (now - cached["checked_at"]) < self._cache_ttl_seconds:
                continue
            health_spec = tile.get("health") or {}
            status = self._probe_fn(health_spec) if health_spec else STATUS_UNKNOWN
            with self._lock:
                self._results[tile_id] = {"status": status, "checked_at": now}

    def start_background_refresh(self, *, interval_seconds: Optional[float] = None) -> None:
        if self._thread is not None:
            return
        wait_seconds = float(interval_seconds if interval_seconds is not None else self._cache_ttl_seconds)

        def _run() -> None:
            while not self._stop_event.wait(wait_seconds):
                self._refresh_stale()

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
