from __future__ import annotations

import ipaddress
import os
import threading
import time
from collections.abc import Mapping
from typing import Callable, Optional

try:
    from meshtastic.protobuf import admin_pb2
except Exception:  # pragma: no cover - exercised via runtime fallback
    admin_pb2 = None  # type: ignore[assignment]


_DEFAULT_REFRESH_SECONDS = 20
_DEFAULT_REQUEST_TIMEOUT_SECONDS = 8
_CONNECTION_STATUS_SOURCE = "admin.get_device_connection_status"
_DEFAULT_ENABLED = str(os.getenv("MESHDASH_RADIO_CONNECTION_STATUS_ENABLED", "0")).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
    "y",
}
_ENABLED = _DEFAULT_ENABLED

_CACHE_LOCK = threading.Lock()
_CACHE: dict[int, dict[str, object]] = {}


def _mapping_get(mapping: Mapping[str, object], *keys: str) -> object | None:
    for key in keys:
        if key in mapping:
            return mapping.get(key)
    return None


def _coerce_optional_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        clean = value.strip().lower()
        if clean in {"1", "true", "yes", "on", "y"}:
            return True
        if clean in {"0", "false", "no", "off", "n"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return None


def _coerce_optional_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return None


def _coerce_ipv4_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return str(ipaddress.IPv4Address(text))
        except Exception:
            return text

    numeric = _coerce_optional_int(value)
    if numeric is None or numeric < 0 or numeric > 0xFFFFFFFF:
        return None
    try:
        return str(ipaddress.IPv4Address(numeric))
    except Exception:
        return None


def _parse_network_status(raw: object) -> dict[str, object]:
    if not isinstance(raw, Mapping):
        return {}

    ip_text = _coerce_ipv4_text(_mapping_get(raw, "ip_address", "ipAddress"))
    is_connected = _coerce_optional_bool(_mapping_get(raw, "is_connected", "isConnected"))
    is_mqtt_connected = _coerce_optional_bool(
        _mapping_get(raw, "is_mqtt_connected", "isMqttConnected")
    )
    is_syslog_connected = _coerce_optional_bool(
        _mapping_get(raw, "is_syslog_connected", "isSyslogConnected")
    )

    out: dict[str, object] = {}
    if ip_text:
        out["ip_address"] = ip_text
    if is_connected is not None:
        out["is_connected"] = is_connected
    if is_mqtt_connected is not None:
        out["is_mqtt_connected"] = is_mqtt_connected
    if is_syslog_connected is not None:
        out["is_syslog_connected"] = is_syslog_connected
    return out


def _parse_wifi_status(raw: object) -> dict[str, object]:
    if not isinstance(raw, Mapping):
        return {}
    out = _parse_network_status(_mapping_get(raw, "status"))
    ssid_raw = _mapping_get(raw, "ssid")
    if ssid_raw is not None:
        ssid = str(ssid_raw).strip()
        if ssid:
            out["ssid"] = ssid
    rssi = _coerce_optional_int(_mapping_get(raw, "rssi"))
    if rssi is not None:
        out["rssi_dbm"] = rssi
    return out


def _parse_ethernet_status(raw: object) -> dict[str, object]:
    if not isinstance(raw, Mapping):
        return {}
    return _parse_network_status(_mapping_get(raw, "status"))


def _parse_bluetooth_status(raw: object) -> dict[str, object]:
    if not isinstance(raw, Mapping):
        return {}

    out: dict[str, object] = {}
    pin = _coerce_optional_int(_mapping_get(raw, "pin"))
    if pin is not None:
        out["pin"] = pin
    rssi = _coerce_optional_int(_mapping_get(raw, "rssi"))
    if rssi is not None:
        out["rssi_dbm"] = rssi
    is_connected = _coerce_optional_bool(_mapping_get(raw, "is_connected", "isConnected"))
    if is_connected is not None:
        out["is_connected"] = is_connected
    return out


def _parse_serial_status(raw: object) -> dict[str, object]:
    if not isinstance(raw, Mapping):
        return {}

    out: dict[str, object] = {}
    baud = _coerce_optional_int(_mapping_get(raw, "baud"))
    if baud is not None:
        out["baud"] = baud
    is_connected = _coerce_optional_bool(_mapping_get(raw, "is_connected", "isConnected"))
    if is_connected is not None:
        out["is_connected"] = is_connected
    return out


def _parse_device_connection_status_packet(
    packet: object,
    *,
    now_ts_fn: Callable[[], float] = time.time,
) -> dict[str, object] | None:
    if not isinstance(packet, Mapping):
        return None

    decoded = packet.get("decoded")
    if not isinstance(decoded, Mapping):
        return None

    admin_payload = decoded.get("admin")
    if not isinstance(admin_payload, Mapping):
        return None

    response = _mapping_get(
        admin_payload,
        "getDeviceConnectionStatusResponse",
        "get_device_connection_status_response",
    )
    if not isinstance(response, Mapping):
        return None

    out: dict[str, object] = {
        "source": _CONNECTION_STATUS_SOURCE,
        "captured_at_unix": int(max(0, now_ts_fn())),
    }

    wifi = _parse_wifi_status(_mapping_get(response, "wifi"))
    ethernet = _parse_ethernet_status(_mapping_get(response, "ethernet"))
    bluetooth = _parse_bluetooth_status(_mapping_get(response, "bluetooth"))
    serial = _parse_serial_status(_mapping_get(response, "serial"))

    if wifi:
        out["wifi"] = wifi
    if ethernet:
        out["ethernet"] = ethernet
    if bluetooth:
        out["bluetooth"] = bluetooth
    if serial:
        out["serial"] = serial
    if len(out) <= 2:
        return None
    return out


def _resolve_local_node(iface: object) -> object | None:
    local_node = getattr(iface, "localNode", None)
    if local_node is not None:
        return local_node
    get_node = getattr(iface, "getNode", None)
    if callable(get_node):
        try:
            return get_node("^local")
        except Exception:
            return None
    return None


def _request_connection_status(
    *,
    iface: object,
    cache_key: int,
    now_ts_fn: Callable[[], float] = time.time,
) -> None:
    if admin_pb2 is None:
        with _CACHE_LOCK:
            entry = _CACHE.setdefault(cache_key, {})
            entry["in_flight"] = False
            entry["last_error"] = "Connection status protobuf unavailable"
        return

    local_node = _resolve_local_node(iface)
    send_admin = getattr(local_node, "_sendAdmin", None)
    if not callable(send_admin):
        with _CACHE_LOCK:
            entry = _CACHE.setdefault(cache_key, {})
            entry["in_flight"] = False
            entry["last_error"] = "Admin connection status request unsupported"
        return

    message = admin_pb2.AdminMessage()
    message.get_device_connection_status_request = True

    def _on_response(packet: object) -> None:
        parsed = _parse_device_connection_status_packet(packet, now_ts_fn=now_ts_fn)
        with _CACHE_LOCK:
            entry = _CACHE.setdefault(cache_key, {})
            entry["in_flight"] = False
            if parsed is not None:
                entry["status"] = parsed
                entry["last_response_unix"] = float(now_ts_fn())
                entry["last_error"] = None
            else:
                entry["last_error"] = "Invalid connection status response"

    try:
        send_admin(message, wantResponse=True, onResponse=_on_response)
    except Exception as exc:
        with _CACHE_LOCK:
            entry = _CACHE.setdefault(cache_key, {})
            entry["in_flight"] = False
            entry["last_error"] = str(exc)


def get_radio_connection_status(
    iface: object,
    *,
    now_ts_fn: Callable[[], float] = time.time,
    refresh_seconds: int = _DEFAULT_REFRESH_SECONDS,
    request_timeout_seconds: int = _DEFAULT_REQUEST_TIMEOUT_SECONDS,
) -> dict[str, object] | None:
    with _CACHE_LOCK:
        if not _ENABLED:
            return None

    now = float(now_ts_fn())
    cache_key = id(iface)
    trigger_request = False

    with _CACHE_LOCK:
        entry = _CACHE.setdefault(
            cache_key,
            {
                "status": None,
                "in_flight": False,
                "last_request_unix": 0.0,
                "last_response_unix": 0.0,
                "last_error": None,
            },
        )

        in_flight = bool(entry.get("in_flight"))
        last_request_unix = float(entry.get("last_request_unix") or 0.0)
        if in_flight and (now - last_request_unix) >= max(2.0, float(request_timeout_seconds)):
            entry["in_flight"] = False
            entry["last_error"] = "Connection status request timed out"
            in_flight = False

        should_request = (
            not in_flight
            and (
                last_request_unix <= 0.0
                or (now - last_request_unix) >= max(3.0, float(refresh_seconds))
            )
        )
        if should_request:
            entry["in_flight"] = True
            entry["last_request_unix"] = now
            trigger_request = True

        cached_status = entry.get("status")
        response_unix = float(entry.get("last_response_unix") or 0.0)
        last_error_raw = entry.get("last_error")

    if trigger_request:
        _request_connection_status(
            iface=iface,
            cache_key=cache_key,
            now_ts_fn=now_ts_fn,
        )
        with _CACHE_LOCK:
            cached_status = _CACHE.get(cache_key, {}).get("status")
            response_unix = float(_CACHE.get(cache_key, {}).get("last_response_unix") or 0.0)
            last_error_raw = _CACHE.get(cache_key, {}).get("last_error")

    if isinstance(cached_status, Mapping):
        out = dict(cached_status)
        if response_unix > 0:
            out["age_seconds"] = int(max(0.0, now - response_unix))
        return out

    if last_error_raw:
        error = str(last_error_raw).strip()
        if error:
            return {"error": error}
    return None


def set_radio_connection_status_enabled(enabled: bool) -> bool:
    global _ENABLED
    with _CACHE_LOCK:
        _ENABLED = bool(enabled)
        if not _ENABLED:
            for entry in _CACHE.values():
                entry["in_flight"] = False
                entry["last_error"] = None
    return _ENABLED


def radio_connection_status_enabled() -> bool:
    with _CACHE_LOCK:
        return bool(_ENABLED)
