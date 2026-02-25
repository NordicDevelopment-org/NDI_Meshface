from typing import Any, Mapping, Protocol


class BodyReader(Protocol):
    def read(self, size: int = -1) -> bytes:
        ...


class BodyWriter(Protocol):
    def write(self, data: bytes) -> Any:
        ...


class DashboardHttpHandler(Protocol):
    path: str
    headers: Mapping[str, Any]
    rfile: BodyReader
    wfile: BodyWriter

    def send_response(self, code: int) -> None:
        ...

    def send_header(self, key: str, value: str) -> None:
        ...

    def end_headers(self) -> None:
        ...
