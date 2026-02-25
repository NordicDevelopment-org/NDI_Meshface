from typing import Any

from .http_route_contracts import StateFn, WriteJsonResponseFn


def handle_state_get(
    handler: Any,
    *,
    state_fn: StateFn,
    write_json_response_fn: WriteJsonResponseFn,
) -> None:
    write_json_response_fn(handler, status_code=200, payload_obj=state_fn(), no_store=True)
