from typing import Any, Callable, Dict


def ensure_runtime_dependencies(*, meshtastic_module: Any, pub_module: Any) -> None:
    if meshtastic_module is None:
        raise RuntimeError(
            "meshtastic Python package is required. Install with: pip install meshtastic"
        )
    if pub_module is None:
        raise RuntimeError(
            "pypubsub is required. Install with: pip install pypubsub"
        )


def build_dashboard_runtime_dependencies(
    *,
    meshtastic_module: Any,
    pub_module: Any,
    mesh_target_label_fn: Callable[[Any], str],
    open_mesh_interface_fn: Callable[[Any], Any],
    history_store_cls: Any,
    dashboard_tracker_cls: Any,
    seed_tracker_fn: Callable[..., None],
    revision_info_fn: Callable[[], dict],
    build_state_fn: Callable[..., dict],
    sensitive_field_names: set[str],
    build_node_history_loader_fn: Callable[..., Callable[..., dict]],
    build_online_activity_loader_fn: Callable[..., Callable[..., dict]],
    send_chat_message_fn: Callable[..., dict],
    send_emoji_reaction_packet_fn: Callable[..., Any],
    mesh_pb2_module: Any,
    portnums_pb2_module: Any,
    get_local_node_id_fn: Callable[..., str],
    to_jsonable_fn: Callable[[Any], Any],
    normalize_single_emoji_fn: Callable[[Any], Any],
    to_int_fn: Callable[[Any], Any],
    utc_now_fn: Callable[[], str],
    render_html_fn: Callable[..., str],
    make_http_handler_fn: Callable[..., Any],
    default_node_history_hours: int,
    guess_lan_ipv4_fn: Callable[[], Any],
    default_chat_max_bytes: int,
) -> Dict[str, Any]:
    return {
        "mesh_target_label_fn": mesh_target_label_fn,
        "open_mesh_interface_fn": open_mesh_interface_fn,
        "history_store_cls": history_store_cls,
        "dashboard_tracker_cls": dashboard_tracker_cls,
        "subscribe_fn": pub_module.subscribe,
        "seed_tracker_fn": seed_tracker_fn,
        "revision_info_fn": revision_info_fn,
        "build_state_fn": lambda **kwargs: build_state_fn(
            sensitive_field_names=sensitive_field_names,
            **kwargs,
        ),
        "build_node_history_loader_fn": build_node_history_loader_fn,
        "build_online_activity_loader_fn": build_online_activity_loader_fn,
        "send_chat_message_fn": send_chat_message_fn,
        "send_reaction_packet_fn": lambda **kwargs: send_emoji_reaction_packet_fn(
            mesh_pb2_module=mesh_pb2_module,
            portnums_pb2_module=portnums_pb2_module,
            **kwargs,
        ),
        "get_local_node_id_fn": lambda iface: get_local_node_id_fn(
            iface,
            meshtastic_module=meshtastic_module,
            to_jsonable_fn=to_jsonable_fn,
            to_int_fn=to_int_fn,
        ),
        "normalize_single_emoji_fn": normalize_single_emoji_fn,
        "to_int_fn": to_int_fn,
        "utc_now_fn": utc_now_fn,
        "render_html_fn": render_html_fn,
        "make_http_handler_fn": lambda html_text, state_fn, node_history_fn=None, online_activity_fn=None, send_chat_fn=None: make_http_handler_fn(
            html_text=html_text,
            state_fn=state_fn,
            node_history_fn=node_history_fn,
            online_activity_fn=online_activity_fn,
            send_chat_fn=send_chat_fn,
            default_node_history_hours=default_node_history_hours,
            to_int_fn=to_int_fn,
        ),
        "guess_lan_ipv4_fn": guess_lan_ipv4_fn,
        "default_chat_max_bytes": default_chat_max_bytes,
    }
