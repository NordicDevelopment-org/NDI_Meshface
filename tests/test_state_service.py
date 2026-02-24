from meshdash.state_service import build_dashboard_state


class _DummyTracker:
    def __init__(self):
        self.snapshot_by_id = None

    def snapshot(self, by_id):
        self.snapshot_by_id = by_id
        return {
            "live_packet_count": 4,
            "real_edge_count": 2,
            "edges": [{"from": "!a", "to": "!b", "count": 1}],
            "port_counts": [{"portnum": "TEXT_MESSAGE_APP", "count": 3}],
            "recent_packets": [{"summary": {"packet_id": 1}, "packet": {"id": 1}}],
            "recent_chat": [{"text": "hello"}],
        }

    def load_node_saved_counts(self):
        return {
            "!a": {
                "saved_packets": 7,
                "saved_points": 3,
                "saved_last_seen": "2026-01-01 00:00:00Z",
            }
        }

    def load_node_capabilities(self):
        return {"!a": {"gps_capable": True}}


def test_build_dashboard_state_builds_payload_and_redacts():
    tracker = _DummyTracker()
    observed = {}
    rows = [{"id": "!a"}]

    def _collect_nodes(_iface):
        return {
            "rows": rows,
            "full": [{"id": "!a", "info": {"x": 1}}],
            "by_id": {"!a": {"id": "!a"}},
            "with_position_count": 1,
        }

    def _apply_node_saved_counts(node_rows, saved_counts):
        observed["saved_counts_rows"] = node_rows
        observed["saved_counts"] = saved_counts
        node_rows[0]["saved_packets"] = 7

    def _collect_local_state_safe(_iface, *, collect_local_state_fn):
        observed["collect_local_state_fn"] = collect_local_state_fn
        return {"local_config": {"lora": {"modem_preset": "LONG_FAST"}}}, None

    def _build_summary_payload(**kwargs):
        observed["summary_kwargs"] = kwargs
        return {"summary_ok": True}

    def _redact_secrets(state, sensitive_names):
        observed["redact_state"] = state
        observed["sensitive_names"] = sensitive_names
        return {"redacted": True}

    payload = build_dashboard_state(
        iface=type("_Iface", (), {"myInfo": {"password": "x"}, "metadata": {"board": "x1"}})(),
        tracker=tracker,
        started_at=0.0,
        target="192.168.1.109:4403 (tcp)",
        show_secrets=False,
        storage_probe_path=".",
        revision_info={"version": "0.1.0"},
        sensitive_field_names={"password"},
        collect_nodes_fn=_collect_nodes,
        collect_local_state_fn=lambda iface: {},
        collect_local_state_safe_fn=_collect_local_state_safe,
        modem_preset_from_local_state_fn=lambda state: "LONG_FAST",
        apply_node_saved_counts_fn=_apply_node_saved_counts,
        build_summary_payload_fn=_build_summary_payload,
        to_jsonable_fn=lambda value: value,
        redact_secrets_fn=_redact_secrets,
        utc_now_fn=lambda: "2026-02-24T00:00:00Z",
    )

    assert payload == {"redacted": True}
    assert tracker.snapshot_by_id == {"!a": {"id": "!a"}}
    assert observed["saved_counts_rows"] is rows
    assert observed["saved_counts"]["!a"]["saved_packets"] == 7
    assert observed["summary_kwargs"]["target"] == "192.168.1.109:4403 (tcp)"
    assert observed["summary_kwargs"]["modem_preset"] == "LONG_FAST"
    assert observed["summary_kwargs"]["tracker_data"]["live_packet_count"] == 4
    assert observed["redact_state"]["nodes"][0]["saved_packets"] == 7
    assert observed["redact_state"]["history_caps"]["!a"]["gps_capable"] is True
    assert observed["redact_state"]["traffic"]["recent_chat"][0]["text"] == "hello"
    assert observed["sensitive_names"] == {"password"}


def test_build_dashboard_state_returns_unredacted_payload_when_show_secrets():
    tracker = _DummyTracker()
    rows = [{"id": "!a"}]
    redact_called = {"value": False}

    payload = build_dashboard_state(
        iface=type("_Iface", (), {"myInfo": {"password": "x"}, "metadata": {"board": "x1"}})(),
        tracker=tracker,
        started_at=0.0,
        target="target",
        show_secrets=True,
        storage_probe_path=".",
        revision_info={"version": "0.1.0"},
        sensitive_field_names={"password"},
        collect_nodes_fn=lambda iface: {
            "rows": rows,
            "full": [{"id": "!a", "info": {}}],
            "by_id": {"!a": {"id": "!a"}},
            "with_position_count": 1,
        },
        collect_local_state_fn=lambda iface: {},
        collect_local_state_safe_fn=lambda iface, *, collect_local_state_fn: ({}, None),
        modem_preset_from_local_state_fn=lambda state: None,
        apply_node_saved_counts_fn=lambda node_rows, saved_counts: None,
        build_summary_payload_fn=lambda **kwargs: {"summary_ok": True},
        to_jsonable_fn=lambda value: value,
        redact_secrets_fn=lambda state, names: redact_called.__setitem__("value", True),
        utc_now_fn=lambda: "2026-02-24T00:00:00Z",
    )

    assert payload["generated_at"] == "2026-02-24T00:00:00Z"
    assert payload["summary"]["summary_ok"] is True
    assert redact_called["value"] is False
