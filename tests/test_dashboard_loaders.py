from meshdash.dashboard_loaders import DashboardRuntimeLoaders, build_dashboard_runtime_loaders


def test_build_dashboard_runtime_loaders_wires_all_loader_factories():
    captured = {}

    def _state_snapshot_loader(**kwargs):
        captured["state"] = kwargs
        return lambda: {"state": True}

    def _node_history_loader(**kwargs):
        captured["node_history"] = kwargs
        return lambda *_a, **_k: {"node_history": True}

    def _online_loader(**kwargs):
        captured["online"] = kwargs
        return lambda *_a, **_k: {"online": True}

    def _send_chat_loader(**kwargs):
        captured["send"] = kwargs
        return lambda **_k: {"send": True}

    result = build_dashboard_runtime_loaders(
        iface="iface",
        tracker="tracker",
        send_lock="lock",
        started_at=123.0,
        target="target",
        show_secrets=False,
        history_db_path="/tmp/db.sqlite3",
        revision_info={"version": "0.1.0"},
        history_store="history",
        default_node_history_hours=72,
        default_node_history_points=1440,
        send_chat_message_fn="send_chat_message_fn",
        send_reaction_packet_fn="send_reaction_packet_fn",
        get_local_node_id_fn="get_local_node_id_fn",
        default_chat_max_bytes=220,
        normalize_single_emoji_fn="normalize_single_emoji_fn",
        to_int_fn="to_int_fn",
        utc_now_fn="utc_now_fn",
        build_state_fn="build_state_fn",
        build_state_snapshot_loader_fn=_state_snapshot_loader,
        build_node_history_loader_fn=_node_history_loader,
        build_online_activity_loader_fn=_online_loader,
        build_send_chat_loader_fn=_send_chat_loader,
    )

    assert isinstance(result, DashboardRuntimeLoaders)
    assert callable(result.state_fn)
    assert callable(result.node_history_fn)
    assert callable(result.online_activity_fn)
    assert callable(result.send_chat_fn)
    assert captured["state"]["iface"] == "iface"
    assert captured["state"]["build_state_fn"] == "build_state_fn"
    assert captured["node_history"]["default_hours"] == 72
    assert captured["node_history"]["default_points"] == 1440
    assert captured["online"]["default_hours"] == 72
    assert captured["send"]["chat_max_bytes"] == 220
    assert captured["send"]["send_lock"] == "lock"
