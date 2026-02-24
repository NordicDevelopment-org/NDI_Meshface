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
from .runtime_callbacks import (
    build_send_chat_loader,
    build_state_snapshot_loader,
)
from .dashboard_setup import (
    open_optional_history_store,
    seed_tracker_if_empty,
)
from .dashboard_loaders import (
    build_dashboard_runtime_loaders,
)
from .dashboard_server import (
    build_dashboard_server,
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

    history_db_path = os.path.abspath(os.path.expanduser(args.history_db))
    history_store: Optional[Any] = open_optional_history_store(
        args,
        history_store_cls=history_store_cls,
        history_db_path=history_db_path,
    )

    tracker = dashboard_tracker_cls(packet_limit=args.packet_limit, history_store=history_store)
    send_lock = threading.Lock()
    subscribe_fn(tracker.on_receive, "meshtastic.receive")
    seed_tracker_if_empty(tracker, iface, seed_tracker_fn=seed_tracker_fn)
    started_at = time.time()
    revision_info = revision_info_fn()

    loaders = build_dashboard_runtime_loaders(
        iface=iface,
        tracker=tracker,
        send_lock=send_lock,
        started_at=started_at,
        target=target,
        show_secrets=args.show_secrets,
        history_db_path=history_db_path,
        revision_info=revision_info,
        history_store=history_store,
        default_node_history_hours=args.node_history_hours,
        default_node_history_points=args.node_history_max_points,
        send_chat_message_fn=send_chat_message_fn,
        send_reaction_packet_fn=send_reaction_packet_fn,
        get_local_node_id_fn=get_local_node_id_fn,
        default_chat_max_bytes=default_chat_max_bytes,
        normalize_single_emoji_fn=normalize_single_emoji_fn,
        to_int_fn=to_int_fn,
        utc_now_fn=utc_now_fn,
        build_state_fn=build_state_fn,
        build_state_snapshot_loader_fn=build_state_snapshot_loader,
        build_node_history_loader_fn=build_node_history_loader_fn,
        build_online_activity_loader_fn=build_online_activity_loader_fn,
        build_send_chat_loader_fn=build_send_chat_loader,
    )
    state_fn = loaders["state_fn"]
    node_history_fn = loaders["node_history_fn"]
    online_activity_fn = loaders["online_activity_fn"]
    send_chat_fn = loaders["send_chat_fn"]

    server_parts = build_dashboard_server(
        args=args,
        revision_info=revision_info,
        history_enabled=history_store is not None,
        state_fn=state_fn,
        node_history_fn=node_history_fn,
        online_activity_fn=online_activity_fn,
        send_chat_fn=send_chat_fn,
        render_html_fn=render_html_fn,
        make_http_handler_fn=make_http_handler_fn,
        threading_http_server_cls=threading_http_server_cls,
    )
    server = server_parts["server"]
    bound_host = server_parts["bound_host"]
    bound_port = server_parts["bound_port"]

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
