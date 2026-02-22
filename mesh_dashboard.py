import argparse
import json
import os
import threading
import time
from http.server import ThreadingHTTPServer
from typing import Any, Dict, Optional

try:
    import meshtastic
except Exception:
    meshtastic = None
from mesh_connection import add_mesh_connection_args, mesh_target_label, open_mesh_interface
try:
    from meshdash import __version__ as _package_version
except Exception:
    _package_version = "0.0.0"
from meshdash.helpers import (
    format_epoch as _format_epoch,
    is_sensitive_key as _is_sensitive_key_helper,
    normalize_single_emoji as _normalize_single_emoji,
    redact_secrets as _redact_secrets_helper,
    to_jsonable as _to_jsonable_helper,
    to_int as _to_int,
)
from meshdash.revision import (
    detect_git_commit as _detect_git_commit_helper,
    revision_info as _build_revision_info,
    sanitize_revision_token as _sanitize_revision_token_helper,
)
from meshdash.nodes import (
    get_local_node_id as _get_local_node_id_helper,
    get_local_node_num as _get_local_node_num_helper,
    safe_nodes_items as _safe_nodes_items_helper,
    utc_now as _utc_now_helper,
)
from meshdash.runtime import (
    apply_default_gateway as _apply_default_gateway_helper,
    guess_lan_ipv4 as _guess_lan_ipv4_helper,
)
from meshdash.state import (
    build_state as _build_state_helper,
    collect_local_state as _collect_local_state_helper,
    collect_nodes as _collect_nodes_helper,
)
from meshdash.services import (
    build_node_history_loader as _build_node_history_loader,
    build_online_activity_loader as _build_online_activity_loader,
    send_chat_message as _send_chat_message_helper,
)
from meshdash.history_store import HistoryStore
from meshdash.tracker import DashboardTracker
from meshdash.html import render_html as _render_html_helper
from meshdash.http_api import make_http_handler as _make_http_handler_helper
try:
    from pubsub import pub
except Exception:
    pub = None

try:
    from meshtastic.protobuf import mesh_pb2, portnums_pb2
except Exception:
    mesh_pb2 = None
    portnums_pb2 = None


DEFAULT_MESH_PORT = "/dev/ttyACM0"
DEFAULT_GATEWAY_HOST = "192.168.1.241"
DEFAULT_GATEWAY_PORT = 4403
DEFAULT_HTTP_HOST = "0.0.0.0"
DEFAULT_HTTP_PORT = 8877
DEFAULT_REFRESH_MS = 3000
DEFAULT_PACKET_LIMIT = 250
DEFAULT_HISTORY_DB = "mesh_dashboard_history.sqlite3"
DEFAULT_HISTORY_MAX_ROWS = 5000
DEFAULT_HISTORY_RETENTION_DAYS = 7
DEFAULT_HISTORY_EVENT_MAX_ROWS = 200000
DEFAULT_HISTORY_EVENT_RETENTION_DAYS = 30
DEFAULT_HISTORY_ROLLUP_RETENTION_DAYS = 365
DEFAULT_NODE_HISTORY_HOURS = 72
DEFAULT_NODE_HISTORY_MAX_POINTS = 1440
DEFAULT_CHAT_MAX_BYTES = 220
DEFAULT_APP_VERSION = _package_version or "0.1.0"
UNKNOWN_GIT_COMMIT = "nogit"

SENSITIVE_FIELD_NAMES = {
    "private_key",
    "wifi_psk",
    "password",
    "psk",
    "session_passkey",
    "admin_key",
}


def _utc_now() -> str:
    return _utc_now_helper()


def _sanitize_revision_token(raw: Any, fallback: str) -> str:
    return _sanitize_revision_token_helper(raw, fallback)


def _detect_git_commit() -> Optional[str]:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()
    explicit = os.environ.get("MESH_DASH_GIT_COMMIT", "")
    return _detect_git_commit_helper(
        explicit_commit=explicit,
        script_dir=script_dir,
        cwd=cwd,
        unknown_git_commit=UNKNOWN_GIT_COMMIT,
        sanitize_token=_sanitize_revision_token,
    )


def _revision_info() -> Dict[str, str]:
    version_raw = os.environ.get("MESH_DASH_VERSION", DEFAULT_APP_VERSION)
    return _build_revision_info(
        version_raw=version_raw,
        default_version=DEFAULT_APP_VERSION,
        unknown_git_commit=UNKNOWN_GIT_COMMIT,
        detect_commit=_detect_git_commit,
        sanitize_token=_sanitize_revision_token,
    )


def _send_emoji_reaction_packet(
    iface: Any,
    destination_id: str,
    channel_index: int,
    reply_id: int,
    emoji_codepoint: int,
    emoji_text: str,
    want_ack: bool = False,
) -> Any:
    if mesh_pb2 is None or portnums_pb2 is None:
        raise RuntimeError("Meshtastic protobuf modules are unavailable for emoji reactions")
    if not hasattr(iface, "_sendPacket"):
        raise RuntimeError("Meshtastic interface does not support low-level packet send")

    packet = mesh_pb2.MeshPacket()
    packet.channel = int(channel_index)
    packet.decoded.portnum = portnums_pb2.PortNum.TEXT_MESSAGE_APP
    packet.decoded.reply_id = int(reply_id)
    packet.decoded.emoji = int(emoji_codepoint)
    packet.decoded.payload = str(emoji_text or "").encode("utf-8")
    return iface._sendPacket(packet, destinationId=destination_id, wantAck=bool(want_ack))


def _guess_lan_ipv4() -> Optional[str]:
    return _guess_lan_ipv4_helper()


def _get_local_node_num(iface: Any) -> Optional[int]:
    return _get_local_node_num_helper(iface, to_jsonable_fn=_to_jsonable, to_int_fn=_to_int)


def _get_local_node_id(iface: Any) -> str:
    broadcast_num = getattr(meshtastic, "BROADCAST_NUM", None) if meshtastic is not None else None
    return _get_local_node_id_helper(
        iface,
        broadcast_num=broadcast_num,
        to_jsonable_fn=_to_jsonable,
        to_int_fn=_to_int,
    )


def _apply_default_gateway(args: argparse.Namespace) -> None:
    _apply_default_gateway_helper(args, default_mesh_port=DEFAULT_MESH_PORT)


def _to_jsonable(value: Any, depth: int = 0) -> Any:
    return _to_jsonable_helper(value, depth=depth)


def _is_sensitive_key(key: str) -> bool:
    return _is_sensitive_key_helper(key, SENSITIVE_FIELD_NAMES)


def _redact_secrets(value: Any, parent_key: Optional[str] = None) -> Any:
    return _redact_secrets_helper(value, SENSITIVE_FIELD_NAMES, parent_key=parent_key)


def _seed_tracker_from_node_db(tracker: DashboardTracker, iface: Any) -> None:
    for _num, node in _safe_nodes_items_helper(iface, retries=3, sleep_seconds=0.01):
        if not isinstance(node, dict):
            continue
        last_packet = node.get("lastReceived")
        if isinstance(last_packet, dict):
            tracker.seed_packet(last_packet, iface)


def _collect_nodes(iface: Any) -> Dict[str, Any]:
    return _collect_nodes_helper(iface)


def _collect_local_state(iface: Any) -> Dict[str, Any]:
    return _collect_local_state_helper(iface)


def _build_state(
    iface: Any,
    tracker: DashboardTracker,
    started_at: float,
    target: str,
    show_secrets: bool,
    storage_probe_path: Optional[str],
    revision_info: Dict[str, str],
) -> Dict[str, Any]:
    return _build_state_helper(
        iface=iface,
        tracker=tracker,
        started_at=started_at,
        target=target,
        show_secrets=show_secrets,
        storage_probe_path=storage_probe_path,
        revision_info=revision_info,
        sensitive_field_names=SENSITIVE_FIELD_NAMES,
    )


def _render_html(
    refresh_ms: int,
    packet_limit: int,
    show_secrets: bool,
    history_enabled: bool,
    history_max_rows: int,
    history_retention_days: int,
    node_history_hours: int,
    node_history_max_points: int,
    revision_label: str,
    revision_title: str,
) -> str:
    return _render_html_helper(
        refresh_ms=refresh_ms,
        packet_limit=packet_limit,
        show_secrets=show_secrets,
        history_enabled=history_enabled,
        history_max_rows=history_max_rows,
        history_retention_days=history_retention_days,
        node_history_hours=node_history_hours,
        node_history_max_points=node_history_max_points,
        revision_label=revision_label,
        revision_title=revision_title,
    )


def _make_http_handler(
    html_text: str,
    state_fn,
    node_history_fn=None,
    online_activity_fn=None,
    send_chat_fn=None,
):
    return _make_http_handler_helper(
        html_text=html_text,
        state_fn=state_fn,
        node_history_fn=node_history_fn,
        online_activity_fn=online_activity_fn,
        send_chat_fn=send_chat_fn,
        default_node_history_hours=DEFAULT_NODE_HISTORY_HOURS,
        to_int_fn=_to_int,
    )


def run_dashboard(args: argparse.Namespace) -> None:
    if meshtastic is None:
        raise RuntimeError(
            "meshtastic Python package is required. Install with: pip install meshtastic"
        )
    if pub is None:
        raise RuntimeError(
            "pypubsub is required. Install with: pip install pypubsub"
        )
    target = mesh_target_label(args)
    print(f"Connecting to {target} ...")
    iface = open_mesh_interface(args)

    history_store: Optional[HistoryStore] = None
    history_db_path = os.path.abspath(os.path.expanduser(args.history_db))
    if not args.no_history:
        try:
            history_store = HistoryStore(
                db_path=history_db_path,
                max_rows=args.history_max_rows,
                retention_days=args.history_retention_days,
                event_max_rows=args.history_event_max_rows,
                event_retention_days=args.history_event_retention_days,
                rollup_retention_days=args.history_rollup_retention_days,
            )
        except Exception as exc:
            print(f"History disabled: cannot open {history_db_path}: {exc}")
            history_store = None

    tracker = DashboardTracker(packet_limit=args.packet_limit, history_store=history_store)
    send_lock = threading.Lock()
    pub.subscribe(tracker.on_receive, "meshtastic.receive")
    if not tracker.has_recent_packets():
        _seed_tracker_from_node_db(tracker, iface)
    started_at = time.time()
    revision_info = _revision_info()

    def state_fn() -> Dict[str, Any]:
        return _build_state(
            iface=iface,
            tracker=tracker,
            started_at=started_at,
            target=target,
            show_secrets=args.show_secrets,
            storage_probe_path=history_db_path,
            revision_info=revision_info,
        )

    node_history_fn = _build_node_history_loader(
        history_store=history_store,
        default_hours=args.node_history_hours,
        default_points=args.node_history_max_points,
    )
    online_activity_fn = _build_online_activity_loader(
        history_store=history_store,
        default_hours=args.node_history_hours,
    )

    def send_chat_fn(
        text: Any,
        destination: Any = None,
        channel_index: Optional[int] = None,
        reply_id: Optional[int] = None,
        retry_of: Optional[int] = None,
        emoji: Any = None,
    ) -> Dict[str, Any]:
        return _send_chat_message_helper(
            text=text,
            destination=destination,
            channel_index=channel_index,
            reply_id=reply_id,
            retry_of=retry_of,
            emoji=emoji,
            iface=iface,
            send_lock=send_lock,
            send_reaction_packet_fn=_send_emoji_reaction_packet,
            local_node_id_fn=lambda: _get_local_node_id(iface),
            record_local_chat_fn=tracker.record_local_chat,
            chat_max_bytes=DEFAULT_CHAT_MAX_BYTES,
            normalize_single_emoji_fn=_normalize_single_emoji,
            to_int_fn=_to_int,
            now_text_fn=_utc_now,
        )

    html = _render_html(
        refresh_ms=args.refresh_ms,
        packet_limit=args.packet_limit,
        show_secrets=args.show_secrets,
        history_enabled=history_store is not None,
        history_max_rows=args.history_max_rows,
        history_retention_days=args.history_retention_days,
        node_history_hours=args.node_history_hours,
        node_history_max_points=args.node_history_max_points,
        revision_label=revision_info["label"],
        revision_title=revision_info["title"],
    )
    handler_cls = _make_http_handler(
        html,
        state_fn,
        node_history_fn=node_history_fn,
        online_activity_fn=online_activity_fn,
        send_chat_fn=send_chat_fn,
    )
    server = ThreadingHTTPServer((args.http_host, args.http_port), handler_cls)
    bound_host, bound_port = server.server_address[:2]

    print("Dashboard server running.")
    print(f"Bound to: {bound_host}:{bound_port}")
    if args.http_host in ("0.0.0.0", "::"):
        print(f"Open from this computer: http://127.0.0.1:{bound_port}")
        lan_ip = _guess_lan_ipv4()
        if lan_ip:
            print(f"Open from Wi-Fi devices: http://{lan_ip}:{bound_port}")
        else:
            print(f"Open from Wi-Fi devices: http://<this-computer-ip>:{bound_port}")
    else:
        print(f"Open: http://{args.http_host}:{bound_port}")
    if not args.show_secrets:
        print("Secrets are redacted. Use --show-secrets to display full values.")
    print(f"Revision: v{revision_info['version']} ({revision_info['commit']})")
    if history_store is not None:
        print(
            f"History DB: {history_db_path} "
            f"(retention {args.history_retention_days}d, max {args.history_max_rows} rows; "
            f"events {args.history_event_retention_days}d/{args.history_event_max_rows} rows; "
            f"rollups {args.history_rollup_retention_days}d)"
        )
    else:
        print("History DB: disabled")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        print("Stopping dashboard...")
    finally:
        server.server_close()
        iface.close()
        if history_store is not None:
            history_store.close()


def main() -> None:
    env_gateway_host = os.environ.get("MESH_GATEWAY_HOST", DEFAULT_GATEWAY_HOST)
    env_gateway_port = os.environ.get("MESH_GATEWAY_PORT")
    try:
        resolved_gateway_port = int(env_gateway_port) if env_gateway_port else DEFAULT_GATEWAY_PORT
    except ValueError:
        resolved_gateway_port = DEFAULT_GATEWAY_PORT

    parser = argparse.ArgumentParser(
        description="Serve a high-detail Meshtastic dashboard with map, node tables, configs, and packet logs."
    )
    add_mesh_connection_args(parser, default_mesh_port=DEFAULT_MESH_PORT)
    parser.add_argument(
        "--default-gateway-host",
        default=env_gateway_host,
        help=(
            "Fallback TCP host for dashboard mode when --mesh-host is not provided "
            f"(default: {env_gateway_host})."
        ),
    )
    parser.add_argument(
        "--default-gateway-port",
        type=int,
        default=resolved_gateway_port,
        help=(
            "Fallback TCP port used with --default-gateway-host when --mesh-host is not provided "
            f"(default: {resolved_gateway_port})."
        ),
    )
    parser.add_argument(
        "--no-default-gateway",
        action="store_true",
        help="Disable default gateway fallback and use serial unless --mesh-host is set.",
    )
    parser.add_argument(
        "--http-host",
        default=DEFAULT_HTTP_HOST,
        help=f"HTTP bind host (default: {DEFAULT_HTTP_HOST})",
    )
    parser.add_argument(
        "--http-port",
        type=int,
        default=DEFAULT_HTTP_PORT,
        help=f"HTTP bind port (default: {DEFAULT_HTTP_PORT})",
    )
    parser.add_argument(
        "--refresh-ms",
        type=int,
        default=DEFAULT_REFRESH_MS,
        help=f"Browser polling interval in milliseconds (default: {DEFAULT_REFRESH_MS})",
    )
    parser.add_argument(
        "--packet-limit",
        type=int,
        default=DEFAULT_PACKET_LIMIT,
        help=f"Recent packet history buffer size (default: {DEFAULT_PACKET_LIMIT})",
    )
    parser.add_argument(
        "--show-secrets",
        action="store_true",
        help="Display sensitive config values (private keys/passwords/PSKs) in raw JSON panels.",
    )
    parser.add_argument(
        "--history-db",
        default=os.environ.get("MESH_DASH_HISTORY_DB", DEFAULT_HISTORY_DB),
        help=f"SQLite DB path for persisted chat/packet history and rollups (default: {DEFAULT_HISTORY_DB})",
    )
    parser.add_argument(
        "--history-max-rows",
        type=int,
        default=DEFAULT_HISTORY_MAX_ROWS,
        help=f"Max persisted rows per history table (default: {DEFAULT_HISTORY_MAX_ROWS})",
    )
    parser.add_argument(
        "--history-retention-days",
        type=int,
        default=DEFAULT_HISTORY_RETENTION_DAYS,
        help=(
            "Delete persisted rows older than this many days; "
            f"use 0 to disable age-based pruning (default: {DEFAULT_HISTORY_RETENTION_DAYS})"
        ),
    )
    parser.add_argument(
        "--history-event-max-rows",
        type=int,
        default=DEFAULT_HISTORY_EVENT_MAX_ROWS,
        help=(
            "Max rows for append-only packet event history "
            f"(default: {DEFAULT_HISTORY_EVENT_MAX_ROWS})"
        ),
    )
    parser.add_argument(
        "--history-event-retention-days",
        type=int,
        default=DEFAULT_HISTORY_EVENT_RETENTION_DAYS,
        help=(
            "Delete packet event rows older than this many days; "
            f"use 0 to disable age-based pruning (default: {DEFAULT_HISTORY_EVENT_RETENTION_DAYS})"
        ),
    )
    parser.add_argument(
        "--history-rollup-retention-days",
        type=int,
        default=DEFAULT_HISTORY_ROLLUP_RETENTION_DAYS,
        help=(
            "Delete rollup rows older than this many days; "
            f"use 0 to disable age-based pruning (default: {DEFAULT_HISTORY_ROLLUP_RETENTION_DAYS})"
        ),
    )
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Disable persisted SQLite history (memory-only live buffers).",
    )
    parser.add_argument(
        "--node-history-hours",
        type=int,
        default=DEFAULT_NODE_HISTORY_HOURS,
        help=f"Default selected-node history window in hours (default: {DEFAULT_NODE_HISTORY_HOURS})",
    )
    parser.add_argument(
        "--node-history-max-points",
        type=int,
        default=DEFAULT_NODE_HISTORY_MAX_POINTS,
        help=(
            "Max selected-node history points returned by /api/history/node "
            f"(default: {DEFAULT_NODE_HISTORY_MAX_POINTS})"
        ),
    )
    args = parser.parse_args()
    _apply_default_gateway(args)
    run_dashboard(args)


if __name__ == "__main__":
    main()
