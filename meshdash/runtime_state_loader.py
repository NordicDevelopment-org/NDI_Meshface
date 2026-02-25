from typing import Any, Callable

from .revision import RevisionInfo


def build_state_snapshot_loader(
    *,
    iface: Any,
    tracker: Any,
    started_at: float,
    target: str,
    show_secrets: bool,
    storage_probe_path: str,
    revision_info: RevisionInfo,
    build_state_fn: Callable[..., dict],
) -> Callable[[], dict]:
    def state_fn() -> dict:
        return build_state_fn(
            iface=iface,
            tracker=tracker,
            started_at=started_at,
            target=target,
            show_secrets=show_secrets,
            storage_probe_path=storage_probe_path,
            revision_info=revision_info.as_dict(),
        )

    return state_fn
