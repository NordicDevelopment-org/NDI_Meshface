import argparse
import glob
import os
from typing import Optional

try:
    import meshtastic
except Exception:
    meshtastic = None
from mesh_connection import add_mesh_connection_args, mesh_target_label, open_mesh_interface
try:
    from meshdash import __version__ as _package_version
except Exception:
    _package_version = "0.0.0"
from meshdash.config import (
    DEFAULT_APP_VERSION_FALLBACK,
    DEFAULT_CHAT_MAX_BYTES,
    DEFAULT_FILE_TRANSFER_ENABLED,
    DEFAULT_FILE_TRANSFER_MAX_BYTES,
    DEFAULT_GATEWAY_HOST,
    DEFAULT_GATEWAY_PORT,
    DEFAULT_HISTORY_DB,
    DEFAULT_HISTORY_EVENT_MAX_ROWS,
    DEFAULT_HISTORY_EVENT_RETENTION_DAYS,
    DEFAULT_HISTORY_MAX_ROWS,
    DEFAULT_HISTORY_RETENTION_DAYS,
    DEFAULT_HISTORY_ROLLUP_RETENTION_DAYS,
    DEFAULT_HTTP_HOST,
    DEFAULT_HTTP_PORT,
    DEFAULT_MESH_PORT,
    DEFAULT_NODE_HISTORY_HOURS,
    DEFAULT_NODE_HISTORY_MAX_POINTS,
    DEFAULT_PACKET_LIMIT,
    DEFAULT_REFRESH_MS,
    DEFAULT_RESET_TICKER_SCALE_ON_RESTART,
    MAX_FILE_TRANSFER_MAX_BYTES,
    MIN_FILE_TRANSFER_MAX_BYTES,
    SENSITIVE_FIELD_NAMES,
    UNKNOWN_GIT_COMMIT,
)
from meshdash.helpers import (
    format_epoch as _format_epoch,
    normalize_single_emoji as _normalize_single_emoji,
    to_jsonable as _to_jsonable_helper,
    to_int as _to_int,
)
from meshdash.nodes import utc_now as _utc_now_helper
from meshdash.nodes_identity import get_local_node_id as _get_local_node_id_helper
from meshdash.packet_send import send_emoji_reaction_packet as _send_emoji_reaction_packet_helper
from meshdash.state_nodes import (
    collect_local_state as _collect_local_state_helper,
    collect_nodes_rows_typed as _collect_nodes_rows_typed_helper,
    collect_nodes_typed as _collect_nodes_typed_helper,
)
from meshdash.state_service import (
    build_dashboard_state as _build_dashboard_state_helper,
    build_dashboard_state_lite as _build_dashboard_state_lite_helper,
)
from meshdash.history_views import (
    build_node_history_loader as _build_node_history_loader,
    build_online_activity_loader as _build_online_activity_loader,
    build_summary_metrics_loader as _build_summary_metrics_loader,
)
from meshdash.services_chat import send_chat_message as _send_chat_message_helper
from meshdash.theme_presets import (
    load_theme_presets as _load_theme_presets_helper,
)
from meshdash.theme_settings import ThemePresetSettings as _ThemePresetSettings
from meshdash.cli import build_dashboard_parser as _build_dashboard_parser_helper
from meshdash.dashboard_runner_impl import run_dashboard_runtime as _run_dashboard_runtime_helper
from meshdash.history.db import (
    open_and_initialize_history_connection as _open_and_initialize_history_connection_helper,
)
from meshdash.history_backfill import (
    backfill_environment_metric_rollups as _backfill_environment_metric_rollups_helper,
)
from meshdash.history_store_runtime import HistoryStore
from meshdash.revision import (
    RevisionInfo,
    detect_git_commit as _detect_git_commit_helper,
    revision_info as _build_revision_info_helper,
)
from meshdash.tracker_runtime import DashboardTracker, seed_tracker_from_node_db as _seed_tracker_from_node_db_helper
from meshdash.html_template import render_html as _render_html_helper
from meshdash.http_api import make_http_handler as _make_http_handler_helper
from meshdash.runtime_lifecycle import guess_lan_ipv4 as _guess_lan_ipv4_helper
from meshdash.wiring_runtime import (
    build_dashboard_runtime_dependencies as _build_dashboard_runtime_dependencies_helper,
    ensure_runtime_dependencies as _ensure_runtime_dependencies_helper,
)
try:
    from pubsub import pub
except Exception:
    pub = None

try:
    from meshtastic.protobuf import mesh_pb2, portnums_pb2
except Exception:
    mesh_pb2 = None
    portnums_pb2 = None


DEFAULT_APP_VERSION = _package_version or DEFAULT_APP_VERSION_FALLBACK


def _normalize_file_transfer_max_bytes(raw_value: object) -> int:
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        parsed = int(DEFAULT_FILE_TRANSFER_MAX_BYTES)
    return max(
        int(MIN_FILE_TRANSFER_MAX_BYTES),
        min(int(MAX_FILE_TRANSFER_MAX_BYTES), parsed),
    )


def _validate_file_transfer_startup_args(
    args: argparse.Namespace,
    *,
    parser: argparse.ArgumentParser,
) -> None:
    enabled = bool(getattr(args, "file_transfer_enable", False))
    normalized_max_bytes = _normalize_file_transfer_max_bytes(
        getattr(args, "file_transfer_max_bytes", DEFAULT_FILE_TRANSFER_MAX_BYTES)
    )
    setattr(args, "file_transfer_max_bytes", normalized_max_bytes)
    if not enabled:
        return
    accepted = bool(
        getattr(args, "accept_file_transfer_traffic_disclaimer", False)
    )
    if not accepted:
        parser.error(
            "File transfer remains disabled until you acknowledge mesh traffic risk. "
            "Re-run with both --file-transfer-enable and "
            "--accept-file-transfer-traffic-disclaimer, or set "
            "MESH_DASH_ACCEPT_FILE_TRANSFER_TRAFFIC_DISCLAIMER=1."
        )
    print(
        "Warning: file transfer is enabled. Large transfers can consume significant "
        "mesh airtime and degrade network responsiveness."
    )
    print(
        f"File transfer size cap: {normalized_max_bytes} bytes "
        f"(clamped to {MIN_FILE_TRANSFER_MAX_BYTES}-{MAX_FILE_TRANSFER_MAX_BYTES})."
    )


def _apply_default_gateway(args: argparse.Namespace) -> None:
    # If the user did not override the transport, prefer the shared TCP gateway.
    if bool(getattr(args, "no_default_gateway", False)):
        return
    if getattr(args, "mesh_host", None):
        return
    if str(getattr(args, "mesh_port", "")) != DEFAULT_MESH_PORT:
        return
    gateway_host = str(getattr(args, "default_gateway_host", "") or "").strip()
    if not gateway_host:
        return
    args.mesh_host = gateway_host
    args.mesh_tcp_port = int(getattr(args, "default_gateway_port", DEFAULT_GATEWAY_PORT))


def _detect_git_commit() -> Optional[str]:
    return _detect_git_commit_helper(
        explicit_commit=os.environ.get("MESH_DASH_GIT_COMMIT", ""),
        script_dir=os.path.dirname(os.path.abspath(__file__)),
        cwd=os.getcwd(),
        unknown_git_commit=UNKNOWN_GIT_COMMIT,
    )


def _revision_info() -> RevisionInfo:
    return _build_revision_info_helper(
        version_raw=os.environ.get("MESH_DASH_VERSION"),
        default_version=DEFAULT_APP_VERSION,
        unknown_git_commit=UNKNOWN_GIT_COMMIT,
        detect_commit=_detect_git_commit,
    )


def _build_theme_preset_settings(args: argparse.Namespace) -> _ThemePresetSettings:
    presets = _load_theme_presets_helper(getattr(args, "theme_presets", None))
    return _ThemePresetSettings(
        presets=presets,
        selected_preset=getattr(args, "theme_preset", None),
        settings_path=getattr(args, "theme_settings_file", None),
    )


def _get_local_node_id(iface: object) -> str:
    broadcast_num = (
        getattr(meshtastic, "BROADCAST_NUM", None)
        if meshtastic is not None
        else None
    )
    return _get_local_node_id_helper(
        iface,
        broadcast_num=broadcast_num,
        to_jsonable_fn=_to_jsonable_helper,
        to_int_fn=_to_int,
    )


def _send_reaction_packet(
    *,
    iface: object,
    destination_id: str,
    channel_index: int,
    reply_id: int,
    emoji_codepoint: int,
    emoji_text: str,
    want_ack: bool,
) -> object:
    return _send_emoji_reaction_packet_helper(
        iface=iface,
        destination_id=destination_id,
        channel_index=channel_index,
        reply_id=reply_id,
        emoji_codepoint=emoji_codepoint,
        emoji_text=emoji_text,
        want_ack=want_ack,
        mesh_pb2_module=mesh_pb2,
        portnums_pb2_module=portnums_pb2,
    )


def _build_state_helper(
    *,
    iface: object,
    tracker: object,
    started_at: float,
    target: str,
    show_secrets: bool,
    storage_probe_path: Optional[str],
    revision_info: object,
    sensitive_field_names: set[str],
) -> dict[str, object]:
    return _build_dashboard_state_helper(
        iface=iface,
        tracker=tracker,
        started_at=started_at,
        target=target,
        show_secrets=show_secrets,
        storage_probe_path=storage_probe_path,
        revision_info=revision_info,
        sensitive_field_names=sensitive_field_names,
        collect_nodes_fn=_collect_nodes_typed_helper,
        collect_local_state_fn=_collect_local_state_helper,
    )


def _build_state_lite_helper(
    *,
    iface: object,
    tracker: object,
    started_at: float,
    target: str,
    show_secrets: bool,
    storage_probe_path: Optional[str],
    revision_info: object,
    sensitive_field_names: set[str],
) -> dict[str, object]:
    return _build_dashboard_state_lite_helper(
        iface=iface,
        tracker=tracker,
        started_at=started_at,
        target=target,
        show_secrets=show_secrets,
        storage_probe_path=storage_probe_path,
        revision_info=revision_info,
        sensitive_field_names=sensitive_field_names,
        collect_nodes_fn=_collect_nodes_rows_typed_helper,
        collect_local_state_fn=_collect_local_state_helper,
    )


def _build_render_html_fn_with_theme(
    args: argparse.Namespace,
    *,
    theme_preset_settings: _ThemePresetSettings | None = None,
):
    settings = theme_preset_settings or _build_theme_preset_settings(args)
    file_transfer_enabled = bool(getattr(args, "file_transfer_enable", False))
    file_transfer_max_bytes = _normalize_file_transfer_max_bytes(
        getattr(args, "file_transfer_max_bytes", DEFAULT_FILE_TRANSFER_MAX_BYTES)
    )

    def _render_html_with_theme(**kwargs):
        selected = settings.selected_preset_tokens()
        return _render_html_helper(
            **kwargs,
            light_theme_vars=selected.get("light"),
            dark_theme_vars=selected.get("dark"),
            file_transfer_enabled=file_transfer_enabled,
            file_transfer_max_bytes=file_transfer_max_bytes,
        )

    return _render_html_with_theme


def _build_make_http_handler_with_theme_settings(
    theme_settings: _ThemePresetSettings,
    *,
    api_token: object = None,
    private_mode: bool = False,
):
    clean_api_token = str(api_token or "").strip() or None

    def _make_http_handler_with_theme_settings(
        html_text: str,
        state_fn,
        node_history_fn=None,
        online_activity_fn=None,
        summary_metrics_fn=None,
        send_chat_fn=None,
        default_node_history_hours: int = 72,
        to_int_fn=_to_int,
    ):
        return _make_http_handler_helper(
            html_text=html_text,
            state_fn=state_fn,
            node_history_fn=node_history_fn,
            online_activity_fn=online_activity_fn,
            summary_metrics_fn=summary_metrics_fn,
            send_chat_fn=send_chat_fn,
            get_theme_settings_fn=theme_settings.get_settings_payload,
            set_theme_preset_fn=theme_settings.apply_settings,
            api_token=clean_api_token,
            private_mode=bool(private_mode),
            default_node_history_hours=default_node_history_hours,
            to_int_fn=to_int_fn,
        )

    return _make_http_handler_with_theme_settings


def _resolve_backfill_history_db_path(raw_history_db: object) -> tuple[str, list[str]]:
    resolved = os.path.abspath(os.path.expanduser(str(raw_history_db or DEFAULT_HISTORY_DB)))
    if ".radio-" in os.path.basename(resolved):
        return resolved, []
    root, ext = os.path.splitext(resolved)
    candidate_pattern = f"{root}.radio-*{ext}"
    candidates = [path for path in glob.glob(candidate_pattern) if os.path.isfile(path)]
    if not candidates:
        return resolved, []
    candidates.sort(key=lambda path: os.path.getmtime(path), reverse=True)
    return candidates[0], candidates


def run_environment_rollup_backfill(args: argparse.Namespace) -> None:
    selected_db_path, candidates = _resolve_backfill_history_db_path(getattr(args, "history_db", ""))
    reset_existing = bool(getattr(args, "backfill_environment_rollups_reset", False))
    if candidates:
        print(
            f"Backfill DB selected: {selected_db_path} "
            f"(found {len(candidates)} profiled DB candidate(s))."
        )
    else:
        print(f"Backfill DB selected: {selected_db_path}")
    conn = _open_and_initialize_history_connection_helper(
        db_path=selected_db_path,
        retention_seconds=max(0, int(getattr(args, "history_retention_days", 0))) * 86400,
        event_retention_seconds=max(0, int(getattr(args, "history_event_retention_days", 0))) * 86400,
        rollup_retention_seconds=max(0, int(getattr(args, "history_rollup_retention_days", 0))) * 86400,
        max_rows=max(100, int(getattr(args, "history_max_rows", 100))),
        event_max_rows=max(1000, int(getattr(args, "history_event_max_rows", 1000))),
    )
    try:
        result = _backfill_environment_metric_rollups_helper(
            conn,
            reset_existing=reset_existing,
            commit_every=1000,
        )
        conn.commit()
    finally:
        conn.close()

    print(
        "Environment rollup backfill complete: "
        f"scanned={int(result.get('scanned_packets', 0))}, "
        f"usable={int(result.get('usable_packets', 0))}, "
        f"bad={int(result.get('bad_rows', 0))}, "
        f"rows_before={int(result.get('before_rows', 0))}, "
        f"rows_after={int(result.get('after_rows', 0))}, "
        f"rows_delta={int(result.get('delta_rows', 0))}"
    )


def run_dashboard(args: argparse.Namespace) -> None:
    theme_preset_settings = _build_theme_preset_settings(args)
    _ensure_runtime_dependencies_helper(
        meshtastic_module=meshtastic,
        pub_module=pub,
    )
    runtime_dependencies = _build_dashboard_runtime_dependencies_helper(
        pub_module=pub,
        mesh_target_label_fn=mesh_target_label,
        open_mesh_interface_fn=open_mesh_interface,
        history_store_cls=HistoryStore,
        dashboard_tracker_cls=DashboardTracker,
        seed_tracker_fn=_seed_tracker_from_node_db_helper,
        revision_info_fn=_revision_info,
        build_state_fn=_build_state_helper,
        build_state_lite_fn=_build_state_lite_helper,
        sensitive_field_names=SENSITIVE_FIELD_NAMES,
        build_node_history_loader_fn=_build_node_history_loader,
        build_online_activity_loader_fn=_build_online_activity_loader,
        build_summary_metrics_loader_fn=_build_summary_metrics_loader,
        send_chat_message_fn=_send_chat_message_helper,
        send_reaction_packet_fn=_send_reaction_packet,
        get_local_node_id_fn=_get_local_node_id,
        normalize_single_emoji_fn=_normalize_single_emoji,
        to_int_fn=_to_int,
        utc_now_fn=_utc_now_helper,
        render_html_fn=_build_render_html_fn_with_theme(
            args,
            theme_preset_settings=theme_preset_settings,
        ),
        make_http_handler_fn=_build_make_http_handler_with_theme_settings(
            theme_preset_settings,
            api_token=getattr(args, "api_token", None),
            private_mode=bool(getattr(args, "private_mode", False)),
        ),
        default_node_history_hours=DEFAULT_NODE_HISTORY_HOURS,
        guess_lan_ipv4_fn=_guess_lan_ipv4_helper,
        default_chat_max_bytes=DEFAULT_CHAT_MAX_BYTES,
    )
    _run_dashboard_runtime_helper(
        args,
        mesh_target_label_fn=runtime_dependencies.mesh_target_label_fn,
        open_mesh_interface_fn=runtime_dependencies.open_mesh_interface_fn,
        history_store_cls=runtime_dependencies.history_store_cls,
        dashboard_tracker_cls=runtime_dependencies.dashboard_tracker_cls,
        subscribe_fn=runtime_dependencies.subscribe_fn,
        seed_tracker_fn=runtime_dependencies.seed_tracker_fn,
        revision_info_fn=runtime_dependencies.revision_info_fn,
        build_state_fn=runtime_dependencies.build_state_fn,
        build_node_history_loader_fn=runtime_dependencies.build_node_history_loader_fn,
        build_online_activity_loader_fn=runtime_dependencies.build_online_activity_loader_fn,
        build_summary_metrics_loader_fn=runtime_dependencies.build_summary_metrics_loader_fn,
        send_chat_message_fn=runtime_dependencies.send_chat_message_fn,
        send_reaction_packet_fn=runtime_dependencies.send_reaction_packet_fn,
        get_local_node_id_fn=runtime_dependencies.get_local_node_id_fn,
        normalize_single_emoji_fn=runtime_dependencies.normalize_single_emoji_fn,
        to_int_fn=runtime_dependencies.to_int_fn,
        utc_now_fn=runtime_dependencies.utc_now_fn,
        render_html_fn=runtime_dependencies.render_html_fn,
        make_http_handler_fn=runtime_dependencies.make_http_handler_fn,
        guess_lan_ipv4_fn=runtime_dependencies.guess_lan_ipv4_fn,
        default_chat_max_bytes=runtime_dependencies.default_chat_max_bytes,
    )


def main() -> None:
    parser = _build_dashboard_parser_helper(
        add_mesh_connection_args_fn=add_mesh_connection_args,
        default_mesh_port=DEFAULT_MESH_PORT,
        default_gateway_host=DEFAULT_GATEWAY_HOST,
        default_gateway_port=DEFAULT_GATEWAY_PORT,
        env_gateway_host=os.environ.get("MESH_GATEWAY_HOST", DEFAULT_GATEWAY_HOST),
        env_gateway_port=os.environ.get("MESH_GATEWAY_PORT"),
        default_http_host=DEFAULT_HTTP_HOST,
        default_http_port=DEFAULT_HTTP_PORT,
        default_refresh_ms=DEFAULT_REFRESH_MS,
        default_packet_limit=DEFAULT_PACKET_LIMIT,
        default_reset_ticker_scale_on_restart=DEFAULT_RESET_TICKER_SCALE_ON_RESTART,
        default_history_db=DEFAULT_HISTORY_DB,
        env_history_db=os.environ.get("MESH_DASH_HISTORY_DB"),
        default_history_max_rows=DEFAULT_HISTORY_MAX_ROWS,
        default_history_retention_days=DEFAULT_HISTORY_RETENTION_DAYS,
        default_history_event_max_rows=DEFAULT_HISTORY_EVENT_MAX_ROWS,
        default_history_event_retention_days=DEFAULT_HISTORY_EVENT_RETENTION_DAYS,
        default_history_rollup_retention_days=DEFAULT_HISTORY_ROLLUP_RETENTION_DAYS,
        default_node_history_hours=DEFAULT_NODE_HISTORY_HOURS,
        default_node_history_max_points=DEFAULT_NODE_HISTORY_MAX_POINTS,
        env_theme_presets=os.environ.get("MESH_DASH_THEME_PRESETS"),
        env_theme_preset=os.environ.get("MESH_DASH_THEME_PRESET"),
        env_theme_settings_file=os.environ.get("MESH_DASH_THEME_SETTINGS_FILE"),
        env_private_mode=os.environ.get("MESH_DASH_PRIVATE_MODE"),
        env_api_token=os.environ.get("MESH_DASH_API_TOKEN"),
        default_file_transfer_enable=DEFAULT_FILE_TRANSFER_ENABLED,
        default_file_transfer_max_bytes=DEFAULT_FILE_TRANSFER_MAX_BYTES,
        env_file_transfer_enable=os.environ.get("MESH_DASH_FILE_TRANSFER_ENABLE"),
        env_file_transfer_max_bytes=os.environ.get("MESH_DASH_FILE_TRANSFER_MAX_BYTES"),
        env_accept_file_transfer_traffic_disclaimer=os.environ.get(
            "MESH_DASH_ACCEPT_FILE_TRANSFER_TRAFFIC_DISCLAIMER"
        ),
    )
    args = parser.parse_args()
    _validate_file_transfer_startup_args(args, parser=parser)
    if bool(getattr(args, "backfill_environment_rollups", False)):
        run_environment_rollup_backfill(args)
        return
    _apply_default_gateway(args)
    run_dashboard(args)


if __name__ == "__main__":
    main()
