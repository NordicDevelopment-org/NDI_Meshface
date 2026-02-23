from typing import Any, Callable


def build_state_builder(
    *,
    build_state_fn: Callable[..., dict],
    sensitive_field_names: set[str],
) -> Callable[..., dict]:
    def state_with_sensitive_fields(**kwargs: Any) -> dict:
        return build_state_fn(
            sensitive_field_names=sensitive_field_names,
            **kwargs,
        )

    return state_with_sensitive_fields


def build_reaction_sender(
    *,
    send_emoji_reaction_packet_fn: Callable[..., Any],
    mesh_pb2_module: Any,
    portnums_pb2_module: Any,
) -> Callable[..., Any]:
    def send_reaction_packet(**kwargs: Any) -> Any:
        return send_emoji_reaction_packet_fn(
            mesh_pb2_module=mesh_pb2_module,
            portnums_pb2_module=portnums_pb2_module,
            **kwargs,
        )

    return send_reaction_packet


def build_local_node_id_getter(
    *,
    get_local_node_id_fn: Callable[..., str],
    meshtastic_module: Any,
    to_jsonable_fn: Callable[[Any], Any],
    to_int_fn: Callable[[Any], Any],
) -> Callable[[Any], str]:
    def get_local_node_id(iface: Any) -> str:
        return get_local_node_id_fn(
            iface,
            meshtastic_module=meshtastic_module,
            to_jsonable_fn=to_jsonable_fn,
            to_int_fn=to_int_fn,
        )

    return get_local_node_id


def build_http_handler_factory(
    *,
    make_http_handler_fn: Callable[..., Any],
    default_node_history_hours: int,
    to_int_fn: Callable[[Any], Any],
) -> Callable[..., Any]:
    def make_http_handler(
        html_text: str,
        state_fn: Callable[[], dict],
        node_history_fn: Any = None,
        online_activity_fn: Any = None,
        send_chat_fn: Any = None,
    ) -> Any:
        return make_http_handler_fn(
            html_text=html_text,
            state_fn=state_fn,
            node_history_fn=node_history_fn,
            online_activity_fn=online_activity_fn,
            send_chat_fn=send_chat_fn,
            default_node_history_hours=default_node_history_hours,
            to_int_fn=to_int_fn,
        )

    return make_http_handler
