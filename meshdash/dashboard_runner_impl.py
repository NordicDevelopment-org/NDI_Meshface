import threading
import time
from dataclasses import dataclass
from typing import Optional
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
    DashboardRuntimeContext,
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


@dataclass(frozen=True)
class _NoopCloseResource:
    def close(self) -> None:
        return


class _OfflineTracker:
    def stop_receiving(self) -> None:
        return


_SUMMARY_SAMPLE_INTERVAL_SECONDS = 30.0
_SUMMARY_SAMPLE_STARTUP_DELAY_SECONDS = 5.0


def _summary_sampling_supported(context: DashboardRuntimeContext) -> bool:
    if not context.history_enabled:
        return False
    store = context.history_store
    if store is None:
        return False
    save_summary_fn = getattr(store, "save_summary_metrics", None)
    return callable(save_summary_fn)


def _resolve_summary_sampler_state_fn(state_fn: object):
    lite_fn = getattr(state_fn, "lite", None)
    if callable(lite_fn):
        return lite_fn
    return state_fn if callable(state_fn) else None


def _start_summary_sampler(context: DashboardRuntimeContext) -> tuple[threading.Event | None, threading.Thread | None]:
    if not _summary_sampling_supported(context):
        return None, None
    sample_state_fn = _resolve_summary_sampler_state_fn(context.state_fn)
    if sample_state_fn is None:
        return None, None

    # Prime the latest bucket at startup so charts are populated even before
    # the first background interval elapses.
    try:
        sample_state_fn()
    except Exception:
        pass

    stop_event = threading.Event()

    def _sample_loop() -> None:
        if stop_event.wait(_SUMMARY_SAMPLE_STARTUP_DELAY_SECONDS):
            return
        while not stop_event.wait(_SUMMARY_SAMPLE_INTERVAL_SECONDS):
            try:
                sample_state_fn()
            except Exception:
                # Sampling is best-effort; never take down runtime on metrics write.
                pass

    thread = threading.Thread(
        target=_sample_loop,
        name="dashboard-summary-sampler",
        daemon=True,
    )
    thread.start()
    return stop_event, thread


def _enable_serial_auto_reconnect(args: DashboardArgs) -> bool:
    # Meshtastic TCPInterface has its own reconnect path. Serial links do not,
    # so recover by rebuilding a fresh runtime session.
    mesh_host = str(getattr(args, "mesh_host", "") or "").strip()
    return mesh_host == ""


def _build_offline_state_loader(
    *,
    target: str,
    revision_info: object,
    startup_error: Exception,
    started_at: float,
    utc_now_fn: UtcNowFn,
):
    revision_payload = {}
    as_dict = getattr(revision_info, "as_dict", None)
    if callable(as_dict):
        try:
            revision_payload = dict(as_dict())
        except Exception:
            revision_payload = {}
    startup_error_text = str(startup_error).strip() or "radio unavailable"
    tracker_error_text = f"radio link lost: {startup_error_text}"

    def state_fn() -> dict[str, object]:
        uptime_seconds = int(max(0, time.time() - started_at))
        return {
            "generated_at": utc_now_fn(),
            "summary": {
                "target": target,
                "uptime_seconds": uptime_seconds,
                "node_count": 0,
                "nodes_with_position": 0,
                "live_packet_count": 0,
                "edge_count": 0,
                "real_edge_count": 0,
                "recent_packet_buffer": 0,
                "modem_preset": None,
                "disk": {"free_percent": "n/a"},
                "revision": revision_payload,
            },
            "summary_error": None,
            "my_info": None,
            "my_info_error": None,
            "metadata": None,
            "metadata_error": None,
            "local_state": {},
            "local_state_error": startup_error_text,
            "nodes_error": startup_error_text,
            "tracker_error": tracker_error_text,
            "tracker_saved_counts_error": None,
            "tracker_capabilities_error": None,
            "nodes": [],
            "history_caps": {},
            "nodes_full": [],
            "traffic": {
                "edges": [],
                "port_counts": [],
                "recent_packets": [],
                "recent_chat": [],
            },
            "local_node_id": "local",
        }

    def state_fn_lite() -> dict[str, object]:
        payload = dict(state_fn())
        payload.pop("my_info", None)
        payload.pop("metadata", None)
        payload.pop("local_state", None)
        payload.pop("nodes_full", None)
        return payload

    try:
        setattr(state_fn, "lite", state_fn_lite)
    except Exception:
        pass

    return state_fn


def _build_offline_runtime_context(
    args: DashboardArgs,
    *,
    startup_error: Exception,
    mesh_target_label_fn: MeshTargetLabelFn,
    revision_info_fn: RevisionInfoFn,
    utc_now_fn: UtcNowFn,
) -> DashboardRuntimeContext:
    target = mesh_target_label_fn(args)
    revision_info = revision_info_fn()
    started_at = time.time()
    state_fn = _build_offline_state_loader(
        target=target,
        revision_info=revision_info,
        startup_error=startup_error,
        started_at=started_at,
        utc_now_fn=utc_now_fn,
    )
    return DashboardRuntimeContext(
        target=target,
        iface=_NoopCloseResource(),
        history_db_path="",
        history_store=None,
        tracker=_OfflineTracker(),
        send_lock=threading.Lock(),
        started_at=started_at,
        revision_info=revision_info,
        state_fn=state_fn,
        node_history_fn=None,  # type: ignore[arg-type]
        online_activity_fn=None,  # type: ignore[arg-type]
        summary_metrics_fn=None,  # type: ignore[arg-type]
        send_chat_fn=None,  # type: ignore[arg-type]
        history_enabled=False,
    )


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


def _build_runtime_context_once(
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
    default_chat_max_bytes: int,
):
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
    first_session = True
    while True:
        startup_offline = False
        startup_error: Optional[Exception] = None
        if auto_reconnect and first_session:
            try:
                context = _build_runtime_context_once(
                    args,
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
            except Exception as exc:
                startup_offline = True
                startup_error = exc
                print(
                    f"Radio unavailable at startup ({exc}). "
                    "Starting dashboard in offline mode; plug in the radio and restart."
                )
                context = _build_offline_runtime_context(
                    args,
                    startup_error=exc,
                    mesh_target_label_fn=mesh_target_label_fn,
                    revision_info_fn=revision_info_fn,
                    utc_now_fn=utc_now_fn,
                )
        else:
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
        first_session = False

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
        if startup_offline and startup_error is not None:
            print(f"Offline reason: {startup_error}")

        restart_requested = threading.Event()
        stop_watcher = threading.Event()
        watcher_thread: threading.Thread | None = None
        stop_summary_sampler: threading.Event | None = None
        summary_sampler_thread: threading.Thread | None = None
        stop_summary_sampler, summary_sampler_thread = _start_summary_sampler(context)

        if auto_reconnect and not startup_offline and hasattr(context.tracker, "radio_link_connected"):

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
            if stop_summary_sampler is not None:
                stop_summary_sampler.set()
            if summary_sampler_thread is not None:
                summary_sampler_thread.join(timeout=1.0)
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
        if startup_offline:
            return
        if auto_reconnect and restart_requested.is_set():
            print("Radio link lost. Restarting dashboard radio session...")
            time.sleep(1.0)
            continue
        return
