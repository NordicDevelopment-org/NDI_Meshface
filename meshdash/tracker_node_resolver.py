from typing import Any, Callable, Optional


def get_tracker_node_id_from_num(
    iface: Any,
    node_num: Any,
    *,
    meshtastic_module: Any,
    to_int_fn: Callable[[Any], Optional[int]],
    get_node_id_from_num_fn: Callable[..., Optional[str]],
) -> Optional[str]:
    broadcast_num = (
        getattr(meshtastic_module, "BROADCAST_NUM", None)
        if meshtastic_module is not None
        else None
    )
    return get_node_id_from_num_fn(
        iface,
        node_num,
        broadcast_num=broadcast_num,
        to_int_fn=to_int_fn,
    )
