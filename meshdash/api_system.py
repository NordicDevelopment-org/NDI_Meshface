from .http_handler_contracts import DashboardHttpHandler
from .http_route_contracts import StateFn, WriteJsonResponseFn
from .state_payload_contracts import normalize_state_payload_for_api

from urllib.parse import parse_qs


def _truthy_query_flag(query: str, key: str) -> bool:
    """Return True when a query parameter is present and not an explicit false."""
    try:
        params = parse_qs(query or "", keep_blank_values=True)
    except Exception:
        return False
    if key not in params:
        return False
    raw = params.get(key) or [""]
    value = str(raw[0] if raw else "").strip().lower()
    return value not in ("", "0", "false", "no", "off")


def _lite_state_payload(payload: object) -> object:
    """Drop large/raw-only fields to speed up UI polling."""
    if not isinstance(payload, dict):
        return payload
    out = dict(payload)
    # Raw/debug payloads are expensive to serialize + transmit, and the browser
    # doesn't need them for the primary UI views.
    out.pop("my_info", None)
    out.pop("metadata", None)
    out.pop("local_state", None)
    out.pop("nodes_full", None)
    return out


def handle_state_get(
    handler: DashboardHttpHandler,
    *,
    state_fn: StateFn,
    write_json_response_fn: WriteJsonResponseFn,
    query: str = "",
) -> None:
    lite = _truthy_query_flag(query, "lite")
    if lite:
        state_lite_fn = getattr(state_fn, "lite", None)
        if callable(state_lite_fn):
            payload_raw = state_lite_fn()
        else:
            payload_raw = state_fn()
    else:
        payload_raw = state_fn()

    payload = normalize_state_payload_for_api(payload_raw)
    if lite:
        payload = _lite_state_payload(payload)
    write_json_response_fn(handler, status_code=200, payload_obj=payload, no_store=True)
