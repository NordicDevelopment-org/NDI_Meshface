from typing import Any, Callable, Dict, Optional


def build_dashboard_runtime_loaders(
    *,
    iface: Any,
    tracker: Any,
    send_lock: Any,
    started_at: float,
    target: str,
    show_secrets: bool,
    history_db_path: str,
    revision_info: dict,
    history_store: Optional[Any],
    default_node_history_hours: int,
    default_node_history_points: int,
    send_chat_message_fn: Callable[..., dict],
    send_reaction_packet_fn: Callable[..., Any],
    get_local_node_id_fn: Callable[[Any], str],
    default_chat_max_bytes: int,
    normalize_single_emoji_fn: Callable[[Any], tuple[Optional[str], Optional[int]]],
    to_int_fn: Callable[[Any], Optional[int]],
    utc_now_fn: Callable[[], str],
    build_state_fn: Callable[..., dict],
    build_state_snapshot_loader_fn: Callable[..., Callable[[], dict]],
    build_node_history_loader_fn: Callable[..., Callable[..., dict]],
    build_online_activity_loader_fn: Callable[..., Callable[..., dict]],
    build_send_chat_loader_fn: Callable[..., Callable[..., dict]],
) -> Dict[str, Callable[..., Any]]:
    state_fn = build_state_snapshot_loader_fn(
        iface=iface,
        tracker=tracker,
        started_at=started_at,
        target=target,
        show_secrets=show_secrets,
        storage_probe_path=history_db_path,
        revision_info=revision_info,
        build_state_fn=build_state_fn,
    )

    node_history_fn = build_node_history_loader_fn(
        history_store=history_store,
        default_hours=default_node_history_hours,
        default_points=default_node_history_points,
    )
    online_activity_fn = build_online_activity_loader_fn(
        history_store=history_store,
        default_hours=default_node_history_hours,
    )

    send_chat_fn = build_send_chat_loader_fn(
        iface=iface,
        tracker=tracker,
        send_lock=send_lock,
        send_chat_message_fn=send_chat_message_fn,
        send_reaction_packet_fn=send_reaction_packet_fn,
        get_local_node_id_fn=get_local_node_id_fn,
        chat_max_bytes=default_chat_max_bytes,
        normalize_single_emoji_fn=normalize_single_emoji_fn,
        to_int_fn=to_int_fn,
        utc_now_fn=utc_now_fn,
    )

    return {
        "state_fn": state_fn,
        "node_history_fn": node_history_fn,
        "online_activity_fn": online_activity_fn,
        "send_chat_fn": send_chat_fn,
    }
