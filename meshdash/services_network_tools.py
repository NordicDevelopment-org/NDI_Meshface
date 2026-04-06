from __future__ import annotations

import threading

from .api_input_network_tools import NetworkToolRequest
from .helpers import to_int


def _load_meshtastic_modules():
    try:
        from meshtastic.protobuf import channel_pb2, mesh_pb2, portnums_pb2  # type: ignore
    except Exception as exc:
        raise RuntimeError("Meshtastic protobuf support is unavailable") from exc
    return channel_pb2, mesh_pb2, portnums_pb2


def _channel_is_enabled(iface: object, channel_index: int, channel_pb2_module: object) -> bool:
    local_node = getattr(iface, "localNode", None)
    get_channel = getattr(local_node, "getChannelByChannelIndex", None)
    if not callable(get_channel):
        return True
    try:
        channel = get_channel(channel_index)
    except Exception:
        return False
    if channel is None:
        return False
    disabled_role = getattr(getattr(channel_pb2_module, "Channel", None).Role, "DISABLED", None)
    if disabled_role is None:
        return True
    return getattr(channel, "role", None) != disabled_role


def _portnum_matches(value: object, expected_name: str) -> bool:
    text = str(value or "").strip().upper()
    return text == expected_name or text.endswith(f".{expected_name}")


def _routing_error_reason(packet: object) -> str:
    decoded = packet.get("decoded") if isinstance(packet, dict) else None
    routing = decoded.get("routing") if isinstance(decoded, dict) else None
    if not isinstance(routing, dict):
        return ""
    reason = str(routing.get("errorReason") or "").strip().upper()
    if not reason or reason == "NONE":
        return ""
    return reason


def _send_mesh_request(
    *,
    iface: object,
    send_lock,
    message: object,
    destination: str,
    port_num: object,
    channel_index: int,
    timeout_ms: int,
    hop_limit: int | None = None,
    to_int_fn=to_int,
) -> tuple[int | None, object | None]:
    send_data = getattr(iface, "sendData", None)
    if not callable(send_data):
        raise ValueError("Connected interface does not support sendData()")

    done = threading.Event()
    response_box: dict[str, object] = {"packet": None}

    def _on_response(packet: object) -> None:
        response_box["packet"] = packet
        done.set()

    kwargs: dict[str, object] = {
        "destinationId": destination,
        "portNum": port_num,
        "wantResponse": True,
        "onResponse": _on_response,
        "channelIndex": channel_index,
    }
    if hop_limit is not None:
        kwargs["hopLimit"] = hop_limit

    with send_lock:
        sent_packet = send_data(message, **kwargs)

    sent_packet_id = to_int_fn(getattr(sent_packet, "id", None))
    if not done.wait(max(0.1, float(timeout_ms) / 1000.0)):
        return sent_packet_id, None
    return sent_packet_id, response_box.get("packet")


def _error_response(
    request: NetworkToolRequest,
    *,
    summary_label: str,
    detail: str,
) -> dict[str, object]:
    payload = _not_implemented_response(request, summary_label=summary_label, detail=detail)
    payload["console_lines"] = [f"[{summary_label}] {detail}"]
    return payload


def _not_implemented_response(
    request: NetworkToolRequest,
    *,
    summary_label: str,
    detail: str,
) -> dict[str, object]:
    destination = str(request.destination or "").strip() or None
    payload: dict[str, object] = {
        "ok": False,
        "command": request.command,
        "error": detail,
        "console_lines": [f"[{summary_label}] {detail}"],
    }
    if destination:
        payload["destination"] = destination
    if request.channel_index is not None:
        payload["channel_index"] = request.channel_index
    if request.timeout_ms is not None:
        payload["timeout_ms"] = request.timeout_ms
    if request.hop_limit is not None:
        payload["hop_limit"] = request.hop_limit
    if request.telemetry_type is not None:
        payload["telemetry_type"] = request.telemetry_type
    return payload


def _run_request_position(
    request: NetworkToolRequest,
    *,
    iface: object,
    send_lock,
    to_int_fn=to_int,
) -> dict[str, object]:
    destination = str(request.destination or "").strip()
    if not destination:
        raise ValueError("Missing destination")

    channel_pb2, mesh_pb2, portnums_pb2 = _load_meshtastic_modules()
    channel_index = request.channel_index if request.channel_index is not None else 0
    timeout_ms = request.timeout_ms if request.timeout_ms is not None else 8000
    if not _channel_is_enabled(iface, channel_index, channel_pb2):
        return _error_response(
            request,
            summary_label="position",
            detail=f"Channel {channel_index} is not enabled on the local node",
        )

    position_request = mesh_pb2.Position()
    try:
        sent_packet_id, response_packet = _send_mesh_request(
            iface=iface,
            send_lock=send_lock,
            message=position_request,
            destination=destination,
            port_num=portnums_pb2.PortNum.POSITION_APP,
            channel_index=channel_index,
            timeout_ms=timeout_ms,
            to_int_fn=to_int_fn,
        )
    except ValueError as exc:
        return _error_response(
            request,
            summary_label="position",
            detail=str(exc),
        )
    except Exception as exc:
        return _error_response(
            request,
            summary_label="position",
            detail=f"Position request failed: {exc}",
        )

    if response_packet is None:
        return {
            "ok": False,
            "command": "request_position",
            "destination": destination,
            "channel_index": channel_index,
            "sent_packet_id": sent_packet_id,
            "error": "Timed out waiting for position response",
            "console_lines": [f"[position] {destination} | timed out waiting for response"],
        }

    routing_error = _routing_error_reason(response_packet)
    if routing_error:
        return {
            "ok": False,
            "command": "request_position",
            "destination": destination,
            "channel_index": channel_index,
            "sent_packet_id": sent_packet_id,
            "error": f"Position request failed: {routing_error}",
            "console_lines": [f"[position] {destination} | error={routing_error}"],
        }

    decoded = response_packet.get("decoded") if isinstance(response_packet, dict) else None
    if not isinstance(decoded, dict) or not _portnum_matches(decoded.get("portnum"), "POSITION_APP"):
        return {
            "ok": False,
            "command": "request_position",
            "destination": destination,
            "channel_index": channel_index,
            "sent_packet_id": sent_packet_id,
            "error": "Invalid position response payload",
            "console_lines": [f"[position] {destination} | invalid response payload"],
        }

    payload = decoded.get("payload")
    if not isinstance(payload, (bytes, bytearray)):
        return {
            "ok": False,
            "command": "request_position",
            "destination": destination,
            "channel_index": channel_index,
            "sent_packet_id": sent_packet_id,
            "error": "Position response payload missing",
            "console_lines": [f"[position] {destination} | response payload missing"],
        }

    position = mesh_pb2.Position()
    position.ParseFromString(bytes(payload))
    latitude_i = to_int_fn(getattr(position, "latitude_i", None))
    longitude_i = to_int_fn(getattr(position, "longitude_i", None))
    altitude = to_int_fn(getattr(position, "altitude", None))
    precision_bits = to_int_fn(getattr(position, "precision_bits", None))
    lat = (latitude_i * 1e-7) if latitude_i not in (None, 0) else None
    lon = (longitude_i * 1e-7) if longitude_i not in (None, 0) else None
    position_disabled = precision_bits == 0

    console_parts = [f"[position] {destination}"]
    if lat is not None and lon is not None:
        console_parts.append(f"lat={lat:.6f} lon={lon:.6f}")
    else:
        console_parts.append("lat=n/a lon=n/a")
    if altitude not in (None, 0):
        console_parts.append(f"alt={altitude}m")
    if precision_bits is not None:
        console_parts.append(f"precision={precision_bits}")

    return {
        "ok": True,
        "command": "request_position",
        "destination": destination,
        "channel_index": channel_index,
        "sent_packet_id": sent_packet_id,
        "result": {
            "lat": lat,
            "lon": lon,
            "altitude": altitude if altitude not in (None, 0) else None,
            "precision_bits": precision_bits,
            "position_disabled": position_disabled,
        },
        "console_lines": [" | ".join(console_parts)],
    }


def run_network_tool(
    request: NetworkToolRequest,
    *,
    iface: object,
    send_lock,
    to_int_fn=to_int,
) -> dict[str, object]:
    if request.command == "nodes":
        return {
            "ok": False,
            "command": "nodes",
            "error": "nodes is handled frontend-only in v1",
            "console_lines": [
                "[nodes] handled frontend-only in v1. Use the console nodes aliases instead.",
            ],
        }
    if request.command == "request_position":
        return _run_request_position(
            request,
            iface=iface,
            send_lock=send_lock,
            to_int_fn=to_int_fn,
        )
    if request.command == "request_telemetry":
        return _not_implemented_response(
            request,
            summary_label="telemetry",
            detail="request_telemetry is not implemented on this dashboard instance yet",
        )
    if request.command == "traceroute":
        return _not_implemented_response(
            request,
            summary_label="traceroute",
            detail="traceroute is not implemented on this dashboard instance yet",
        )
    raise ValueError(f"Unsupported network tool command: {request.command}")


__all__ = ["run_network_tool"]
