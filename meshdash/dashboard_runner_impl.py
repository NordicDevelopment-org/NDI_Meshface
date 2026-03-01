import threading
import time
from http.server import ThreadingHTTPServer

from .dashboard_args_contracts import DashboardArgs
from .dashboard_setup_contracts import DashboardTrackerFactory, HistoryStoreFactory
from .runtime_lifecycle import (
    close_runtime_resources,
    emit_startup_status,
)
from .runtime_callbacks import (
    build_send_chat_loader,
    build_state_snapshot_loader,
)
from .dashboard_runtime_context import (
    build_dashboard_runtime_context,
)
from .dashboard_server import (
    build_dashboard_server,
)
from .runtime_types import (
    BuildNodeHistoryLoaderFn,
    BuildOnlineActivityLoaderFn,
    BuildSummaryMetricsLoaderFn,
    BuildStateFn,
    GetLocalNodeIdFn,
    GuessLanIpv4Fn,
    MakeHttpHandlerFn,
    MeshTargetLabelFn,
    NormalizeSingleEmojiFn,
    OpenMeshInterfaceFn,
    RenderHtmlFn,
    RevisionInfoFn,
    SendChatMessageFn,
    SendReactionPacketFn,
    SeedTrackerFn,
    SubscribeFn,
    ThreadingHttpServerCls,
    ToIntFn,
    UtcNowFn,
)


def _enable_serial_auto_reconnect(args: DashboardArgs) -> bool:
    # Meshtastic TCPInterface has its own reconnect path. Serial links do not,
    # so recover by rebuilding a fresh runtime session.
    mesh_host = str(getattr(args, "mesh_host", "") or "").strip()
    return mesh_host == ""


def _build_runtime_context_with_retry(
    args: DashboardArgs,
    *,
    auto_reconnect: bool,
    mesh_target_label_fn: MeshTargetLabelFn,
    open_mesh_interface_fn: OpenMeshInterfaceFn,
    history_store_cls: HistoryStoreFactory,
    dashboard_tracker_cls: DashboardTrackerFactory,
    subscribe_fn: SubscribeFn,
    seed_tracker_fn: SeedTrackerFn,
    revision_info_fn: RevisionInfoFn,
    build_state_fn: BuildStateFn,
    build_node_history_loader_fn: BuildNodeHistoryLoaderFn,
    build_online_activity_loader_fn: BuildOnlineActivityLoaderFn,
    build_summary_metrics_loader_fn: BuildSummaryMetricsLoaderFn,
    send_chat_message_fn: SendChatMessageFn,
    send_reaction_packet_fn: SendReactionPacketFn,
    get_local_node_id_fn: GetLocalNodeIdFn,
    normalize_single_emoji_fn: NormalizeSingleEmojiFn,
    to_int_fn: ToIntFn,
    utc_now_fn: UtcNowFn,
    default_chat_max_bytes: int,
):
    attempt = 0
    while True:
        try:
            return build_dashboard_runtime_context(
                args,
                mesh_target_label_fn=mesh_target_label_fn,
                open_mesh_interface_fn=open_mesh_interface_fn,
                history_store_cls=history_store_cls,
                dashboard_tracker_cls=dashboard_tracker_cls,
                subscribe_fn=subscribe_fn,
                seed_tracker_fn=seed_tracker_fn,
                revision_info_fn=revision_info_fn,
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
                build_summary_metrics_loader_fn=build_summary_metrics_loader_fn,
                build_send_chat_loader_fn=build_send_chat_loader,
            )
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            if not auto_reconnect:
                raise
            attempt += 1
            delay_seconds = min(10, 1 + attempt)
            print(
                f"Radio unavailable ({exc}). Retrying connection in {delay_seconds}s..."
            )
            time.sleep(delay_seconds)


def run_dashboard_runtime(
    args: DashboardArgs,
    *,
    mesh_target_label_fn: MeshTargetLabelFn,
    open_mesh_interface_fn: OpenMeshInterfaceFn,
    history_store_cls: HistoryStoreFactory,
    dashboard_tracker_cls: DashboardTrackerFactory,
    subscribe_fn: SubscribeFn,
    seed_tracker_fn: SeedTrackerFn,
    revision_info_fn: RevisionInfoFn,
    build_state_fn: BuildStateFn,
    build_node_history_loader_fn: BuildNodeHistoryLoaderFn,
    build_online_activity_loader_fn: BuildOnlineActivityLoaderFn,
    build_summary_metrics_loader_fn: BuildSummaryMetricsLoaderFn,
    send_chat_message_fn: SendChatMessageFn,
    send_reaction_packet_fn: SendReactionPacketFn,
    get_local_node_id_fn: GetLocalNodeIdFn,
    normalize_single_emoji_fn: NormalizeSingleEmojiFn,
    to_int_fn: ToIntFn,
    utc_now_fn: UtcNowFn,
    render_html_fn: RenderHtmlFn,
    make_http_handler_fn: MakeHttpHandlerFn,
    guess_lan_ipv4_fn: GuessLanIpv4Fn,
    default_chat_max_bytes: int,
    threading_http_server_cls: ThreadingHttpServerCls = ThreadingHTTPServer,
) -> None:
    auto_reconnect = _enable_serial_auto_reconnect(args)
    while True:
        context = _build_runtime_context_with_retry(
            args,
            auto_reconnect=auto_reconnect,
            mesh_target_label_fn=mesh_target_label_fn,
            open_mesh_interface_fn=open_mesh_interface_fn,
            history_store_cls=history_store_cls,
            dashboard_tracker_cls=dashboard_tracker_cls,
            subscribe_fn=subscribe_fn,
            seed_tracker_fn=seed_tracker_fn,
            revision_info_fn=revision_info_fn,
            build_state_fn=build_state_fn,
            build_node_history_loader_fn=build_node_history_loader_fn,
            build_online_activity_loader_fn=build_online_activity_loader_fn,
            build_summary_metrics_loader_fn=build_summary_metrics_loader_fn,
            send_chat_message_fn=send_chat_message_fn,
            send_reaction_packet_fn=send_reaction_packet_fn,
            get_local_node_id_fn=get_local_node_id_fn,
            normalize_single_emoji_fn=normalize_single_emoji_fn,
            to_int_fn=to_int_fn,
            utc_now_fn=utc_now_fn,
            default_chat_max_bytes=default_chat_max_bytes,
        )

        server_parts = build_dashboard_server(
            args=args,
            revision_info=context.revision_info,
            history_enabled=context.history_enabled,
            state_fn=context.state_fn,
            node_history_fn=context.node_history_fn,
            online_activity_fn=context.online_activity_fn,
            summary_metrics_fn=context.summary_metrics_fn,
            send_chat_fn=context.send_chat_fn,
            render_html_fn=render_html_fn,
            make_http_handler_fn=make_http_handler_fn,
            threading_http_server_cls=threading_http_server_cls,
        )
        server = server_parts.server
        bound_host = server_parts.bound_host
        bound_port = server_parts.bound_port

        emit_startup_status(
            http_host=args.http_host,
            bound_host=bound_host,
            bound_port=bound_port,
            show_secrets=args.show_secrets,
            revision_info=context.revision_info,
            history_enabled=context.history_enabled,
            history_db_path=context.history_db_path,
            history_retention_days=args.history_retention_days,
            history_max_rows=args.history_max_rows,
            history_event_retention_days=args.history_event_retention_days,
            history_event_max_rows=args.history_event_max_rows,
            history_rollup_retention_days=args.history_rollup_retention_days,
            guess_lan_ipv4_fn=guess_lan_ipv4_fn,
        )

        restart_requested = threading.Event()
        stop_watcher = threading.Event()
        watcher_thread: threading.Thread | None = None

        if auto_reconnect and hasattr(context.tracker, "radio_link_connected"):

            def _watch_radio_link_loss() -> None:
                while not stop_watcher.wait(0.5):
                    try:
                        connected = getattr(context.tracker, "radio_link_connected", None)
                    except Exception:
                        connected = None
                    if connected is not False:
                        continue
                    restart_requested.set()
                    shutdown_fn = getattr(server, "shutdown", None)
                    if callable(shutdown_fn):
                        try:
                            shutdown_fn()
                        except Exception:
                            pass
                    return

            watcher_thread = threading.Thread(
                target=_watch_radio_link_loss,
                name="dashboard-radio-watch",
                daemon=True,
            )
            watcher_thread.start()

        interrupted = False
        try:
            server.serve_forever(poll_interval=0.5)
        except KeyboardInterrupt:
            print("Stopping dashboard...")
            interrupted = True
        finally:
            stop_watcher.set()
            if watcher_thread is not None:
                watcher_thread.join(timeout=1.0)
            stop_receiving = getattr(context.tracker, "stop_receiving", None)
            if callable(stop_receiving):
                try:
                    stop_receiving()
                except Exception:
                    pass
            close_runtime_resources(
                server=server,
                iface=context.iface,
                history_store=context.history_store,
            )

        if interrupted:
            return
        if auto_reconnect and restart_requested.is_set():
            print("Radio link lost. Restarting dashboard radio session...")
            time.sleep(1.0)
            continue
        return
