import os
import threading
import time
from http.server import ThreadingHTTPServer
from typing import Any, Callable, Optional

from .runtime_lifecycle import (
    close_runtime_resources,
    emit_startup_status,
    serve_until_stopped,
)


def run_dashboard_runtime(
    args: Any,
    *,
    mesh_target_label_fn: Callable[[Any], str],
    open_mesh_interface_fn: Callable[[Any], Any],
    history_store_cls: Any,
    dashboard_tracker_cls: Any,
    subscribe_fn: Callable[[Any, str], None],
    seed_tracker_fn: Callable[[Any, Any], None],
    revision_info_fn: Callable[[], dict],
    build_state_fn: Callable[..., dict],
    build_node_history_loader_fn: Callable[..., Callable[..., dict]],
    build_online_activity_loader_fn: Callable[..., Callable[..., dict]],
    send_chat_message_fn: Callable[..., dict],
    send_reaction_packet_fn: Callable[..., Any],
    get_local_node_id_fn: Callable[[Any], str],
    normalize_single_emoji_fn: Callable[[Any], tuple[Optional[str], Optional[int]]],
    to_int_fn: Callable[[Any], Optional[int]],
    utc_now_fn: Callable[[], str],
    render_html_fn: Callable[..., str],
    make_http_handler_fn: Callable[..., Any],
    guess_lan_ipv4_fn: Callable[[], Optional[str]],
    default_chat_max_bytes: int,
    threading_http_server_cls: Any = ThreadingHTTPServer,
) -> None:
    target = mesh_target_label_fn(args)
    print(f"Connecting to {target} ...")
    iface = open_mesh_interface_fn(args)

    history_store: Optional[Any] = None
    history_db_path = os.path.abspath(os.path.expanduser(args.history_db))
    if not args.no_history:
        try:
            history_store = history_store_cls(
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

    tracker = dashboard_tracker_cls(packet_limit=args.packet_limit, history_store=history_store)
    send_lock = threading.Lock()
    subscribe_fn(tracker.on_receive, "meshtastic.receive")
    if not tracker.has_recent_packets():
        seed_tracker_fn(tracker, iface)
    started_at = time.time()
    revision_info = revision_info_fn()

    def state_fn() -> dict:
        return build_state_fn(
            iface=iface,
            tracker=tracker,
            started_at=started_at,
            target=target,
            show_secrets=args.show_secrets,
            storage_probe_path=history_db_path,
            revision_info=revision_info,
        )

    node_history_fn = build_node_history_loader_fn(
        history_store=history_store,
        default_hours=args.node_history_hours,
        default_points=args.node_history_max_points,
    )
    online_activity_fn = build_online_activity_loader_fn(
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
    ) -> dict:
        return send_chat_message_fn(
            text=text,
            destination=destination,
            channel_index=channel_index,
            reply_id=reply_id,
            retry_of=retry_of,
            emoji=emoji,
            iface=iface,
            send_lock=send_lock,
            send_reaction_packet_fn=send_reaction_packet_fn,
            local_node_id_fn=lambda: get_local_node_id_fn(iface),
            record_local_chat_fn=tracker.record_local_chat,
            chat_max_bytes=default_chat_max_bytes,
            normalize_single_emoji_fn=normalize_single_emoji_fn,
            to_int_fn=to_int_fn,
            now_text_fn=utc_now_fn,
        )

    html = render_html_fn(
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
    handler_cls = make_http_handler_fn(
        html,
        state_fn,
        node_history_fn=node_history_fn,
        online_activity_fn=online_activity_fn,
        send_chat_fn=send_chat_fn,
    )
    server = threading_http_server_cls((args.http_host, args.http_port), handler_cls)
    bound_host, bound_port = server.server_address[:2]

    emit_startup_status(
        http_host=args.http_host,
        bound_host=bound_host,
        bound_port=bound_port,
        show_secrets=args.show_secrets,
        revision_info=revision_info,
        history_enabled=history_store is not None,
        history_db_path=history_db_path,
        history_retention_days=args.history_retention_days,
        history_max_rows=args.history_max_rows,
        history_event_retention_days=args.history_event_retention_days,
        history_event_max_rows=args.history_event_max_rows,
        history_rollup_retention_days=args.history_rollup_retention_days,
        guess_lan_ipv4_fn=guess_lan_ipv4_fn,
    )
    try:
        serve_until_stopped(server, poll_interval=0.5)
    finally:
        close_runtime_resources(
            server=server,
            iface=iface,
            history_store=history_store,
        )
