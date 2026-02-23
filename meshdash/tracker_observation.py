from typing import Any, Dict


def apply_tracker_observation(
    *,
    parsed: Dict[str, Any],
    include_live_count: bool,
    session_edges: Dict[Any, Dict[str, Any]],
    historical_edges: Dict[Any, Dict[str, Any]],
    port_counts: Any,
    apply_routing_delivery_update_fn,
    extract_update_fn,
    set_delivery_state_fn,
    record_direct_edge_observation_fn,
):
    decoded = parsed["decoded"]
    from_id = parsed["from_id"]
    to_id = parsed["to_id"]
    rx_time = parsed["rx_time"]
    hops = parsed["hops"]
    portnum = parsed["portnum"]

    apply_routing_delivery_update_fn(
        decoded,
        extract_update_fn=extract_update_fn,
        set_delivery_state_fn=set_delivery_state_fn,
    )
    if portnum is not None:
        port_counts[str(portnum)] += 1

    return record_direct_edge_observation_fn(
        session_edges=session_edges,
        historical_edges=historical_edges,
        from_id=from_id,
        to_id=to_id,
        rx_time=rx_time,
        portnum=portnum,
        hops=hops,
        include_live_count=include_live_count,
    )
