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

    # Resolve the function that will be used to build the payload.
    selected_fn = state_fn
    if lite:
        state_lite_fn = getattr(state_fn, "lite", None)
        if callable(state_lite_fn):
            selected_fn = state_lite_fn

    # Conditional GET: if the client already has this version, return 304.
    etag_fn = getattr(selected_fn, "etag", None)
    etag = None
    if callable(etag_fn):
        try:
            etag = str(etag_fn())
        except Exception:
            etag = None

    if etag:
        # BaseHTTPRequestHandler's headers mapping is case-insensitive, but our
        # Protocol is only a Mapping, so be defensive.
        if_none_match = None
        try:
            if_none_match = handler.headers.get("If-None-Match")  # type: ignore[attr-defined]
        except Exception:
            if_none_match = None
        if if_none_match is None:
            for key, value in getattr(handler, "headers", {}).items():
                try:
                    if str(key).lower() == "if-none-match":
                        if_none_match = value
                        break
                except Exception:
                    continue
        if if_none_match is not None and str(if_none_match).strip() == etag:
            handler.send_response(304)
            handler.send_header("Cache-Control", "no-store")
            handler.send_header("ETag", etag)
            handler.send_header("Content-Length", "0")
            handler.end_headers()
            return

    payload_raw = selected_fn()
    payload = normalize_state_payload_for_api(payload_raw)
    if lite:
        payload = _lite_state_payload(payload)
    kwargs = {
        "status_code": 200,
        "payload_obj": payload,
        "no_store": True,
    }
    if etag:
        kwargs["extra_headers"] = {"ETag": etag}
    write_json_response_fn(handler, **kwargs)
