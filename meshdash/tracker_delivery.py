from .runtime_types import ExtractDeliveryUpdateFn, SetDeliveryStateFn


def apply_routing_delivery_update(
    decoded: object,
    *,
    from_id: object = None,
    to_id: object = None,
    extract_update_fn: ExtractDeliveryUpdateFn,
    set_delivery_state_fn: SetDeliveryStateFn,
) -> bool:
    delivery_update = extract_update_fn(decoded)
    if delivery_update is None:
        return False
    set_delivery_state_fn(
        delivery_update.get("request_id"),
        str(delivery_update.get("state") or "sent"),
        delivery_update.get("error"),
        ack_from_id=from_id,
        ack_to_id=to_id,
    )
    return True
