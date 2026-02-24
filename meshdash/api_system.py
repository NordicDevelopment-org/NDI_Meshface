from typing import Any, Callable


def handle_state_get(
    handler: Any,
    *,
    state_fn: Callable[[], dict],
    write_json_response_fn: Callable[..., None],
) -> None:
    write_json_response_fn(handler, status_code=200, payload_obj=state_fn(), no_store=True)
