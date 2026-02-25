from typing import Any, Iterable, Protocol


class TrackerSeedTarget(Protocol):
    def seed_packet(self, packet: dict[str, Any], iface: object) -> None:
        ...


class SafeNodesItemsFn(Protocol):
    def __call__(
        self,
        iface: object,
        *,
        retries: int,
        sleep_seconds: float,
    ) -> Iterable[tuple[Any, Any]]:
        ...
