from typing import Optional

from .runtime_types import GetNodeIdFromNumFn, ToIntFn


def get_tracker_node_id_from_num(
    iface: object,
    node_num: object,
    *,
    meshtastic_module: object,
    to_int_fn: ToIntFn,
    get_node_id_from_num_fn: GetNodeIdFromNumFn,
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
