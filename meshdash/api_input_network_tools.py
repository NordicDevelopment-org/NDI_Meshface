import json
from dataclasses import dataclass

from .helpers import to_int


_COMMAND_ALIASES = {
    "nodes": "nodes",
    "--nodes": "nodes",
    "send-node-info": "send_node_info",
    "--send-node-info": "send_node_info",
    "send_node_info": "send_node_info",
    "send-nodeinfo": "send_node_info",
    "--send-nodeinfo": "send_node_info",
    "ping": "ping",
    "--ping": "ping",
    "nodeinfo": "ping",
    "--nodeinfo": "ping",
    "request-nodeinfo": "ping",
    "--request-nodeinfo": "ping",
    "request_nodeinfo": "ping",
    "traceroute": "traceroute",
    "--traceroute": "traceroute",
    "request-position": "request_position",
    "--request-position": "request_position",
    "request_position": "request_position",
    "request-telemetry": "request_telemetry",
    "--request-telemetry": "request_telemetry",
    "request_telemetry": "request_telemetry",
}

_DESTINATION_OPTIONAL_COMMANDS = {
    "nodes",
    "send_node_info",
}

_TELEMETRY_TYPE_ALIASES = {
    "device": "device_metrics",
    "device_metrics": "device_metrics",
    "environment": "environment_metrics",
    "environment_metrics": "environment_metrics",
    "air_quality": "air_quality_metrics",
    "airquality": "air_quality_metrics",
    "air_quality_metrics": "air_quality_metrics",
    "power": "power_metrics",
    "power_metrics": "power_metrics",
    "localstats": "local_stats",
    "local_stats": "local_stats",
}


@dataclass(frozen=True)
class NetworkToolRequest:
    command: str
    destination: object = None
    channel_index: int | None = None
    timeout_ms: int | None = None
    hop_limit: int | None = None
    telemetry_type: object = None


def _normalize_command(value: object) -> str:
    clean = str(value or "").strip().lower()
    if not clean:
        raise ValueError("Missing command")
    normalized = _COMMAND_ALIASES.get(clean)
    if not normalized:
        raise ValueError(f"Unsupported network tool command: {clean}")
    return normalized


def _normalize_destination(value: object) -> str | None:
    if value is None:
        return None
    clean = str(value).strip()
    return clean or None


def _parse_optional_int(
    value: object,
    *,
    label: str,
    to_int_fn=to_int,
    min_value: int | None = None,
) -> int | None:
    if value is None:
        return None
    numeric = to_int_fn(value)
    if numeric is None:
        raise ValueError(f"Invalid {label}")
    if min_value is not None and numeric < min_value:
        raise ValueError(f"{label} must be >= {min_value}")
    return numeric


def _normalize_telemetry_type(value: object) -> str | None:
    if value is None:
        return None
    clean = str(value).strip().lower()
    if not clean:
        return None
    normalized = _TELEMETRY_TYPE_ALIASES.get(clean)
    if not normalized:
        raise ValueError(f"Unsupported telemetry type: {clean}")
    return normalized


def parse_network_tool_request(
    raw_body: bytes,
    *,
    to_int_fn=to_int,
) -> NetworkToolRequest:
    try:
        body = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Invalid JSON: {exc}")

    if not isinstance(body, dict):
        raise ValueError("Expected a JSON object")

    command = _normalize_command(body.get("command"))
    destination = _normalize_destination(
        body.get("destination", body.get("dest"))
    )
    if command not in _DESTINATION_OPTIONAL_COMMANDS and not destination:
        raise ValueError("Missing destination")

    channel_index = _parse_optional_int(
        body.get("channel_index", body.get("ch_index")),
        label="channel_index",
        to_int_fn=to_int_fn,
        min_value=0,
    )
    timeout_ms = _parse_optional_int(
        body.get("timeout_ms", body.get("timeout")),
        label="timeout_ms",
        to_int_fn=to_int_fn,
        min_value=1,
    )
    hop_limit = _parse_optional_int(
        body.get("hop_limit"),
        label="hop_limit",
        to_int_fn=to_int_fn,
        min_value=1,
    )
    telemetry_type = _normalize_telemetry_type(
        body.get("telemetry_type", body.get("type"))
    )

    return NetworkToolRequest(
        command=command,
        destination=destination,
        channel_index=channel_index,
        timeout_ms=timeout_ms,
        hop_limit=hop_limit,
        telemetry_type=telemetry_type,
    )


__all__ = [
    "NetworkToolRequest",
    "parse_network_tool_request",
]
