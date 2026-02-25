from .http_handler_contracts import DashboardHttpHandler
from .http_route_contracts import StateFn, WriteJsonResponseFn
from .state_payload_contracts import normalize_state_payload_for_api


def handle_state_get(
    handler: DashboardHttpHandler,
    *,
    state_fn: StateFn,
    write_json_response_fn: WriteJsonResponseFn,
) -> None:
    payload = normalize_state_payload_for_api(state_fn())
    write_json_response_fn(handler, status_code=200, payload_obj=payload, no_store=True)
