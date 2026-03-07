from collections.abc import Mapping

from .helpers import to_jsonable


def _mapping_get(obj: object, key: str) -> object | None:
    if isinstance(obj, Mapping):
        return obj.get(key)
    return getattr(obj, key, None)


def _coerce_local_node_num(*candidates: object) -> int | None:
    for candidate in candidates:
        try:
            value = int(candidate)  # type: ignore[arg-type]
        except Exception:
            continue
        if value > 0:
            return value
    return None


def _resolve_local_node_info(iface: object, local_node_num: int | None) -> object | None:
    if local_node_num is None:
        return None

    nodes_by_num = getattr(iface, "nodesByNum", None)
    if isinstance(nodes_by_num, Mapping):
        direct = nodes_by_num.get(local_node_num)
        if direct is None:
            direct = nodes_by_num.get(str(local_node_num))
        if direct is not None:
            return direct

    # Fallback for interfaces that keep node records by ID.
    nodes = getattr(iface, "nodes", None)
    if isinstance(nodes, Mapping):
        local_id = f"!{local_node_num:08x}"
        direct = nodes.get(local_id)
        if direct is not None:
            return direct
        for value in nodes.values():
            if not isinstance(value, Mapping):
                continue
            user = value.get("user")
            if not isinstance(user, Mapping):
                continue
            if str(user.get("id") or "") == local_id:
                return value
    return None


def collect_local_state(iface: object) -> dict[str, object]:
    local = getattr(iface, "localNode", None)
    if local is None:
        local = iface.getNode("^local")

    state: dict[str, object] = {}
    state["local_config"] = to_jsonable(getattr(local, "localConfig", None))
    state["module_config"] = to_jsonable(getattr(local, "moduleConfig", None))
    channels = getattr(local, "channels", None)
    if channels is None:
        state["channels"] = []
    else:
        state["channels"] = [to_jsonable(channel) for channel in channels]

    my_info = getattr(iface, "myInfo", None)
    local_node_num = _coerce_local_node_num(
        _mapping_get(local, "nodeNum"),
        _mapping_get(my_info, "my_node_num"),
        _mapping_get(my_info, "myNodeNum"),
    )
    if local_node_num is not None:
        state["local_node_num"] = local_node_num

    local_node_info = _resolve_local_node_info(iface, local_node_num)
    if local_node_info is not None:
        state["local_node_info"] = to_jsonable(local_node_info)

    # Capture current local position when available so the settings map can
    # restore its marker after reloads even if fixed-position coords are absent
    # from local_config.position.
    local_position = None
    if isinstance(state.get("local_node_info"), Mapping):
        local_position = state["local_node_info"].get("position")
    if local_position is None:
        local_position = _mapping_get(local, "position")
    if local_position is not None:
        state["local_position"] = to_jsonable(local_position)
    return state
