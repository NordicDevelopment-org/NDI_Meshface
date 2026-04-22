import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from meshdash.runtime_lifecycle import close_runtime_resources


class _CloseRecorder:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.closed = False
        self._error = error

    def close(self) -> None:
        self.closed = True
        if self._error is not None:
            raise self._error


class _ServerRecorder:
    def __init__(self, *, error: Exception | None = None) -> None:
        self.closed = False
        self._error = error

    def server_close(self) -> None:
        self.closed = True
        if self._error is not None:
            raise self._error


def test_close_runtime_resources_ignores_interface_close_errors() -> None:
    server = _ServerRecorder()
    iface = _CloseRecorder(error=BrokenPipeError("radio reset"))
    history_store = _CloseRecorder()

    close_runtime_resources(
        server=server,
        iface=iface,
        history_store=history_store,
    )

    assert server.closed is True
    assert iface.closed is True
    assert history_store.closed is True


def test_close_runtime_resources_continues_after_server_close_error() -> None:
    server = _ServerRecorder(error=OSError("server close failed"))
    iface = _CloseRecorder()
    history_store = _CloseRecorder()

    close_runtime_resources(
        server=server,
        iface=iface,
        history_store=history_store,
    )

    assert server.closed is True
    assert iface.closed is True
    assert history_store.closed is True
