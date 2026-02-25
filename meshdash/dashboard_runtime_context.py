import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .dashboard_loaders import (
    DashboardRuntimeLoaders,
    build_dashboard_runtime_loaders,
)
from .revision import RevisionInfo
from .dashboard_setup import (
    open_optional_history_store,
    seed_tracker_if_empty,
)


@dataclass(frozen=True)
class DashboardRuntimeContext:
    target: str
    iface: Any
    history_db_path: str
    history_store: Optional[Any]
    tracker: Any
    send_lock: Any
    started_at: float
    revision_info: RevisionInfo
    state_fn: Callable[[], dict]
    node_history_fn: Callable[..., dict]
    online_activity_fn: Callable[..., dict]
    send_chat_fn: Callable[..., dict]
    history_enabled: bool


def build_dashboard_runtime_context(
    args: Any,
    *,
    mesh_target_label_fn: Callable[[Any], str],
    open_mesh_interface_fn: Callable[[Any], Any],
    history_store_cls: Any,
    dashboard_tracker_cls: Any,
    subscribe_fn: Callable[[Any, str], None],
    seed_tracker_fn: Callable[[Any, Any], None],
    revision_info_fn: Callable[[], RevisionInfo],
    send_chat_message_fn: Callable[..., dict],
    send_reaction_packet_fn: Callable[..., Any],
    get_local_node_id_fn: Callable[[Any], str],
    normalize_single_emoji_fn: Callable[[Any], tuple[Optional[str], Optional[int]]],
    to_int_fn: Callable[[Any], Optional[int]],
    utc_now_fn: Callable[[], str],
    build_state_fn: Callable[..., dict],
    build_state_snapshot_loader_fn: Callable[..., Callable[[], dict]],
    build_node_history_loader_fn: Callable[..., Callable[..., dict]],
    build_online_activity_loader_fn: Callable[..., Callable[..., dict]],
    build_send_chat_loader_fn: Callable[..., Callable[..., dict]],
    default_chat_max_bytes: int,
    print_fn: Callable[[str], None] = print,
    lock_factory: Callable[[], Any] = threading.Lock,
    now_unix_fn: Callable[[], float] = time.time,
    resolve_history_db_path_fn: Callable[[str], str] = lambda path: os.path.abspath(
        os.path.expanduser(path)
    ),
    open_optional_history_store_fn: Callable[..., Optional[Any]] = open_optional_history_store,
    seed_tracker_if_empty_fn: Callable[..., None] = seed_tracker_if_empty,
    build_dashboard_runtime_loaders_fn: Callable[..., DashboardRuntimeLoaders] = build_dashboard_runtime_loaders,
) -> DashboardRuntimeContext:
    target = mesh_target_label_fn(args)
    print_fn(f"Connecting to {target} ...")
    iface = open_mesh_interface_fn(args)

    history_db_path = resolve_history_db_path_fn(args.history_db)
    history_store: Optional[Any] = open_optional_history_store_fn(
        args,
        history_store_cls=history_store_cls,
        history_db_path=history_db_path,
    )

    tracker = dashboard_tracker_cls(packet_limit=args.packet_limit, history_store=history_store)
    send_lock = lock_factory()
    subscribe_fn(tracker.on_receive, "meshtastic.receive")
    seed_tracker_if_empty_fn(tracker, iface, seed_tracker_fn=seed_tracker_fn)
    started_at = now_unix_fn()
    revision_info = revision_info_fn()

    loaders = build_dashboard_runtime_loaders_fn(
        iface=iface,
        tracker=tracker,
        send_lock=send_lock,
        started_at=started_at,
        target=target,
        show_secrets=args.show_secrets,
        history_db_path=history_db_path,
        revision_info=revision_info.as_dict(),
        history_store=history_store,
        default_node_history_hours=args.node_history_hours,
        default_node_history_points=args.node_history_max_points,
        send_chat_message_fn=send_chat_message_fn,
        send_reaction_packet_fn=send_reaction_packet_fn,
        get_local_node_id_fn=get_local_node_id_fn,
        default_chat_max_bytes=default_chat_max_bytes,
        normalize_single_emoji_fn=normalize_single_emoji_fn,
        to_int_fn=to_int_fn,
        utc_now_fn=utc_now_fn,
        build_state_fn=build_state_fn,
        build_state_snapshot_loader_fn=build_state_snapshot_loader_fn,
        build_node_history_loader_fn=build_node_history_loader_fn,
        build_online_activity_loader_fn=build_online_activity_loader_fn,
        build_send_chat_loader_fn=build_send_chat_loader_fn,
    )

    return DashboardRuntimeContext(
        target=target,
        iface=iface,
        history_db_path=history_db_path,
        history_store=history_store,
        tracker=tracker,
        send_lock=send_lock,
        started_at=started_at,
        revision_info=revision_info,
        state_fn=loaders.state_fn,
        node_history_fn=loaders.node_history_fn,
        online_activity_fn=loaders.online_activity_fn,
        send_chat_fn=loaders.send_chat_fn,
        history_enabled=history_store is not None,
    )
