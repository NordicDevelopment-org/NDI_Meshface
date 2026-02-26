from types import MappingProxyType

from meshdash.state_payload_contracts import DashboardStatePayload
from meshdash.revision import RevisionInfo
from meshdash.state_service import build_dashboard_state, build_dashboard_state_typed


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


class _FailingTracker:
    def snapshot(self, by_id):
        raise RuntimeError("snapshot boom")

    def load_node_saved_counts(self):
        raise RuntimeError("saved boom")

    def load_node_capabilities(self):
        raise RuntimeError("caps boom")


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
    assert observed["summary_kwargs"]["tracker_data"].live_packet_count == 4
    assert observed["redact_state"]["summary_error"] is None
    assert observed["redact_state"]["nodes"][0]["saved_packets"] == 7
    assert observed["redact_state"]["history_caps"]["!a"]["gps_capable"] is True
    assert observed["redact_state"]["traffic"]["recent_chat"][0]["text"] == "hello"
    assert observed["redact_state"]["my_info_error"] is None
    assert observed["redact_state"]["metadata_error"] is None
    assert observed["redact_state"]["tracker_error"] is None
    assert observed["redact_state"]["nodes_error"] is None
    assert observed["redact_state"]["tracker_saved_counts_error"] is None
    assert observed["redact_state"]["tracker_capabilities_error"] is None
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
    assert payload["summary_error"] is None
    assert payload["my_info_error"] is None
    assert payload["metadata_error"] is None
    assert redact_called["value"] is False
    assert payload["nodes_error"] is None


def test_build_dashboard_state_handles_tracker_failures_without_crashing():
    tracker = _FailingTracker()
    payload = build_dashboard_state(
        iface=type("_Iface", (), {"myInfo": {}, "metadata": {}})(),
        tracker=tracker,
        started_at=0.0,
        target="target",
        show_secrets=True,
        storage_probe_path=".",
        revision_info={"version": "0.1.0"},
        sensitive_field_names={"password"},
        collect_nodes_fn=lambda iface: {
            "rows": [{"id": "!a"}],
            "full": [{"id": "!a", "info": {}}],
            "by_id": {"!a": {"id": "!a"}},
            "with_position_count": 1,
        },
        collect_local_state_fn=lambda iface: {},
        collect_local_state_safe_fn=lambda iface, *, collect_local_state_fn: ({}, None),
        modem_preset_from_local_state_fn=lambda state: None,
        apply_node_saved_counts_fn=lambda node_rows, saved_counts: None,
        build_summary_payload_fn=lambda **kwargs: {
            "live_packet_count": kwargs["tracker_data"].live_packet_count
        },
        to_jsonable_fn=lambda value: value,
        redact_secrets_fn=lambda state, names: state,
        utc_now_fn=lambda: "2026-02-24T00:00:00Z",
    )

    assert payload["summary"]["live_packet_count"] == 0
    assert payload["tracker_error"] == "snapshot boom"
    assert payload["nodes_error"] is None
    assert payload["tracker_saved_counts_error"] == "saved boom"
    assert payload["tracker_capabilities_error"] == "caps boom"
    assert payload["history_caps"] == {}
    assert payload["traffic"]["edges"] == []
    assert payload["traffic"]["recent_packets"] == []


def test_build_dashboard_state_handles_collect_nodes_failure_without_crashing():
    tracker = _DummyTracker()
    payload = build_dashboard_state(
        iface=type("_Iface", (), {"myInfo": {}, "metadata": {}})(),
        tracker=tracker,
        started_at=0.0,
        target="target",
        show_secrets=True,
        storage_probe_path=".",
        revision_info={"version": "0.1.0"},
        sensitive_field_names={"password"},
        collect_nodes_fn=lambda iface: (_ for _ in ()).throw(RuntimeError("nodes boom")),
        collect_local_state_fn=lambda iface: {},
        collect_local_state_safe_fn=lambda iface, *, collect_local_state_fn: ({}, None),
        modem_preset_from_local_state_fn=lambda state: None,
        apply_node_saved_counts_fn=lambda node_rows, saved_counts: None,
        build_summary_payload_fn=lambda **kwargs: {
            "node_count": len(kwargs["node_rows"]),
            "nodes_with_position": kwargs["nodes_with_position"],
        },
        to_jsonable_fn=lambda value: value,
        redact_secrets_fn=lambda state, names: state,
        utc_now_fn=lambda: "2026-02-24T00:00:00Z",
    )

    assert payload["nodes_error"] == "nodes boom"
    assert payload["nodes"] == []
    assert payload["nodes_full"] == []
    assert payload["summary"]["node_count"] == 0
    assert payload["summary"]["nodes_with_position"] == 0
    assert tracker.snapshot_by_id == {}


def test_build_dashboard_state_handles_to_jsonable_failures_without_crashing():
    tracker = _DummyTracker()

    def _to_jsonable(value):
        if value == "fail-me":
            raise RuntimeError("json boom")
        return value

    payload = build_dashboard_state(
        iface=type("_Iface", (), {"myInfo": "fail-me", "metadata": "fail-me"})(),
        tracker=tracker,
        started_at=0.0,
        target="target",
        show_secrets=True,
        storage_probe_path=".",
        revision_info={"version": "0.1.0"},
        sensitive_field_names={"password"},
        collect_nodes_fn=lambda iface: {
            "rows": [{"id": "!a"}],
            "full": [{"id": "!a", "info": {}}],
            "by_id": {"!a": {"id": "!a"}},
            "with_position_count": 1,
        },
        collect_local_state_fn=lambda iface: {},
        collect_local_state_safe_fn=lambda iface, *, collect_local_state_fn: ({}, None),
        modem_preset_from_local_state_fn=lambda state: None,
        apply_node_saved_counts_fn=lambda node_rows, saved_counts: None,
        build_summary_payload_fn=lambda **kwargs: {"summary_ok": True},
        to_jsonable_fn=_to_jsonable,
        redact_secrets_fn=lambda state, names: state,
        utc_now_fn=lambda: "2026-02-24T00:00:00Z",
    )

    assert payload["my_info"] is None
    assert payload["metadata"] is None
    assert payload["my_info_error"] == "json boom"
    assert payload["metadata_error"] == "json boom"
    assert payload["summary_error"] is None


def test_build_dashboard_state_handles_collect_local_state_safe_loader_failure_without_crashing():
    tracker = _DummyTracker()
    payload = build_dashboard_state(
        iface=type("_Iface", (), {"myInfo": {}, "metadata": {}})(),
        tracker=tracker,
        started_at=0.0,
        target="target",
        show_secrets=True,
        storage_probe_path=".",
        revision_info={"version": "0.1.0"},
        sensitive_field_names={"password"},
        collect_nodes_fn=lambda iface: {
            "rows": [{"id": "!a"}],
            "full": [{"id": "!a", "info": {}}],
            "by_id": {"!a": {"id": "!a"}},
            "with_position_count": 1,
        },
        collect_local_state_fn=lambda iface: {},
        collect_local_state_safe_fn=lambda iface, *, collect_local_state_fn: (_ for _ in ()).throw(
            RuntimeError("local safe boom")
        ),
        modem_preset_from_local_state_fn=lambda state: "LONG_FAST",
        apply_node_saved_counts_fn=lambda node_rows, saved_counts: None,
        build_summary_payload_fn=lambda **kwargs: {"modem_preset": kwargs["modem_preset"]},
        to_jsonable_fn=lambda value: value,
        redact_secrets_fn=lambda state, names: state,
        utc_now_fn=lambda: "2026-02-24T00:00:00Z",
    )

    assert payload["local_state"] == {}
    assert payload["local_state_error"] == "local safe boom"
    assert payload["summary"]["modem_preset"] == "LONG_FAST"


def test_build_dashboard_state_handles_modem_preset_extractor_failure_without_crashing():
    tracker = _DummyTracker()
    payload = build_dashboard_state(
        iface=type("_Iface", (), {"myInfo": {}, "metadata": {}})(),
        tracker=tracker,
        started_at=0.0,
        target="target",
        show_secrets=True,
        storage_probe_path=".",
        revision_info={"version": "0.1.0"},
        sensitive_field_names={"password"},
        collect_nodes_fn=lambda iface: {
            "rows": [{"id": "!a"}],
            "full": [{"id": "!a", "info": {}}],
            "by_id": {"!a": {"id": "!a"}},
            "with_position_count": 1,
        },
        collect_local_state_fn=lambda iface: {},
        collect_local_state_safe_fn=lambda iface, *, collect_local_state_fn: ({}, None),
        modem_preset_from_local_state_fn=lambda state: (_ for _ in ()).throw(RuntimeError("preset boom")),
        apply_node_saved_counts_fn=lambda node_rows, saved_counts: None,
        build_summary_payload_fn=lambda **kwargs: {"modem_preset": kwargs["modem_preset"]},
        to_jsonable_fn=lambda value: value,
        redact_secrets_fn=lambda state, names: state,
        utc_now_fn=lambda: "2026-02-24T00:00:00Z",
    )

    assert payload["local_state_error"] == "preset boom"
    assert payload["summary"]["modem_preset"] is None


def test_build_dashboard_state_handles_apply_node_saved_counts_failure_without_crashing():
    tracker = _DummyTracker()
    payload = build_dashboard_state(
        iface=type("_Iface", (), {"myInfo": {}, "metadata": {}})(),
        tracker=tracker,
        started_at=0.0,
        target="target",
        show_secrets=True,
        storage_probe_path=".",
        revision_info={"version": "0.1.0"},
        sensitive_field_names={"password"},
        collect_nodes_fn=lambda iface: {
            "rows": [{"id": "!a"}],
            "full": [{"id": "!a", "info": {}}],
            "by_id": {"!a": {"id": "!a"}},
            "with_position_count": 1,
        },
        collect_local_state_fn=lambda iface: {},
        collect_local_state_safe_fn=lambda iface, *, collect_local_state_fn: ({}, None),
        modem_preset_from_local_state_fn=lambda state: None,
        apply_node_saved_counts_fn=lambda node_rows, saved_counts: (_ for _ in ()).throw(
            RuntimeError("apply boom")
        ),
        build_summary_payload_fn=lambda **kwargs: {"node_count": len(kwargs["node_rows"])},
        to_jsonable_fn=lambda value: value,
        redact_secrets_fn=lambda state, names: state,
        utc_now_fn=lambda: "2026-02-24T00:00:00Z",
    )

    assert payload["tracker_saved_counts_error"] == "apply boom"
    assert payload["summary"]["node_count"] == 1
    assert payload["nodes"][0]["id"] == "!a"


def test_build_dashboard_state_handles_invalid_local_state_shape_without_crashing():
    tracker = _DummyTracker()
    payload = build_dashboard_state(
        iface=type("_Iface", (), {"myInfo": {}, "metadata": {}})(),
        tracker=tracker,
        started_at=0.0,
        target="target",
        show_secrets=True,
        storage_probe_path=".",
        revision_info={"version": "0.1.0"},
        sensitive_field_names={"password"},
        collect_nodes_fn=lambda iface: {
            "rows": [{"id": "!a"}],
            "full": [{"id": "!a", "info": {}}],
            "by_id": {"!a": {"id": "!a"}},
            "with_position_count": 1,
        },
        collect_local_state_fn=lambda iface: {},
        collect_local_state_safe_fn=lambda iface, *, collect_local_state_fn: (["bad"], None),
        modem_preset_from_local_state_fn=lambda state: "LONG_FAST",
        apply_node_saved_counts_fn=lambda node_rows, saved_counts: None,
        build_summary_payload_fn=lambda **kwargs: {"modem_preset": kwargs["modem_preset"]},
        to_jsonable_fn=lambda value: value,
        redact_secrets_fn=lambda state, names: state,
        utc_now_fn=lambda: "2026-02-24T00:00:00Z",
    )

    assert payload["local_state"] == {}
    assert payload["local_state_error"] == "Expected local_state mapping from collect_local_state_safe_fn"
    assert payload["summary"]["modem_preset"] == "LONG_FAST"


def test_build_dashboard_state_handles_invalid_summary_shape_without_crashing():
    tracker = _DummyTracker()
    payload = build_dashboard_state(
        iface=type("_Iface", (), {"myInfo": {}, "metadata": {}})(),
        tracker=tracker,
        started_at=0.0,
        target="target",
        show_secrets=True,
        storage_probe_path=".",
        revision_info={"version": "0.1.0"},
        sensitive_field_names={"password"},
        collect_nodes_fn=lambda iface: {
            "rows": [{"id": "!a"}],
            "full": [{"id": "!a", "info": {}}],
            "by_id": {"!a": {"id": "!a"}},
            "with_position_count": 1,
        },
        collect_local_state_fn=lambda iface: {},
        collect_local_state_safe_fn=lambda iface, *, collect_local_state_fn: ({}, None),
        modem_preset_from_local_state_fn=lambda state: None,
        apply_node_saved_counts_fn=lambda node_rows, saved_counts: None,
        build_summary_payload_fn=lambda **kwargs: "bad-summary",
        to_jsonable_fn=lambda value: value,
        redact_secrets_fn=lambda state, names: state,
        utc_now_fn=lambda: "2026-02-24T00:00:00Z",
    )

    assert payload["summary_error"] == "Expected summary payload mapping from build_summary_payload_fn"
    assert payload["summary"]["target"] == "target"
    assert payload["summary"]["node_count"] == 1


def test_build_dashboard_state_handles_invalid_tracker_snapshot_shape_without_crashing():
    tracker = _DummyTracker()
    payload = build_dashboard_state(
        iface=type("_Iface", (), {"myInfo": {}, "metadata": {}})(),
        tracker=tracker,
        started_at=0.0,
        target="target",
        show_secrets=True,
        storage_probe_path=".",
        revision_info={"version": "0.1.0"},
        sensitive_field_names={"password"},
        collect_nodes_fn=lambda iface: {
            "rows": [{"id": "!a"}],
            "full": [{"id": "!a", "info": {}}],
            "by_id": {"!a": {"id": "!a"}},
            "with_position_count": 1,
        },
        collect_local_state_fn=lambda iface: {},
        collect_local_state_safe_fn=lambda iface, *, collect_local_state_fn: ({}, None),
        modem_preset_from_local_state_fn=lambda state: None,
        apply_node_saved_counts_fn=lambda node_rows, saved_counts: None,
        build_summary_payload_fn=lambda **kwargs: {
            "live_packet_count": kwargs["tracker_data"].live_packet_count
        },
        load_tracker_snapshot_safe_fn=lambda tracker, nodes_by_id: ("bad-snapshot", None),
        to_jsonable_fn=lambda value: value,
        redact_secrets_fn=lambda state, names: state,
        utc_now_fn=lambda: "2026-02-24T00:00:00Z",
    )

    assert payload["tracker_error"] == "Expected TrackerSnapshot or mapping, got <class 'str'>"
    assert payload["summary"]["live_packet_count"] == 0
    assert payload["traffic"]["edges"] == []


def test_build_dashboard_state_handles_invalid_saved_counts_shape_without_crashing():
    tracker = _DummyTracker()
    payload = build_dashboard_state(
        iface=type("_Iface", (), {"myInfo": {}, "metadata": {}})(),
        tracker=tracker,
        started_at=0.0,
        target="target",
        show_secrets=True,
        storage_probe_path=".",
        revision_info={"version": "0.1.0"},
        sensitive_field_names={"password"},
        collect_nodes_fn=lambda iface: {
            "rows": [{"id": "!a"}],
            "full": [{"id": "!a", "info": {}}],
            "by_id": {"!a": {"id": "!a"}},
            "with_position_count": 1,
        },
        collect_local_state_fn=lambda iface: {},
        collect_local_state_safe_fn=lambda iface, *, collect_local_state_fn: ({}, None),
        modem_preset_from_local_state_fn=lambda state: None,
        apply_node_saved_counts_fn=lambda node_rows, saved_counts: None,
        build_summary_payload_fn=lambda **kwargs: {"summary_ok": True},
        load_tracker_node_saved_counts_safe_fn=lambda tracker: ("bad-saved", None),
        to_jsonable_fn=lambda value: value,
        redact_secrets_fn=lambda state, names: state,
        utc_now_fn=lambda: "2026-02-24T00:00:00Z",
    )

    assert payload["tracker_saved_counts_error"] == "Expected node saved counts mapping"
    assert payload["summary"]["summary_ok"] is True


def test_build_dashboard_state_handles_invalid_capabilities_shape_without_crashing():
    tracker = _DummyTracker()
    payload = build_dashboard_state(
        iface=type("_Iface", (), {"myInfo": {}, "metadata": {}})(),
        tracker=tracker,
        started_at=0.0,
        target="target",
        show_secrets=True,
        storage_probe_path=".",
        revision_info={"version": "0.1.0"},
        sensitive_field_names={"password"},
        collect_nodes_fn=lambda iface: {
            "rows": [{"id": "!a"}],
            "full": [{"id": "!a", "info": {}}],
            "by_id": {"!a": {"id": "!a"}},
            "with_position_count": 1,
        },
        collect_local_state_fn=lambda iface: {},
        collect_local_state_safe_fn=lambda iface, *, collect_local_state_fn: ({}, None),
        modem_preset_from_local_state_fn=lambda state: None,
        apply_node_saved_counts_fn=lambda node_rows, saved_counts: None,
        build_summary_payload_fn=lambda **kwargs: {"summary_ok": True},
        load_tracker_node_capabilities_safe_fn=lambda tracker: ("bad-caps", None),
        to_jsonable_fn=lambda value: value,
        redact_secrets_fn=lambda state, names: state,
        utc_now_fn=lambda: "2026-02-24T00:00:00Z",
    )

    assert payload["tracker_capabilities_error"] == "Expected node capabilities mapping"
    assert payload["history_caps"] == {}
    assert payload["summary"]["summary_ok"] is True


def test_build_dashboard_state_typed_returns_contract_payload():
    tracker = _DummyTracker()
    payload = build_dashboard_state_typed(
        iface=type("_Iface", (), {"myInfo": {"id": "!a"}, "metadata": {"board": "x1"}})(),
        tracker=tracker,
        target="target",
        started_at=0.0,
        storage_probe_path=".",
        revision_info=RevisionInfo(version="0.1.0", commit="abc", label="L", title="T"),
        collect_nodes_fn=lambda iface: {
            "rows": [{"id": "!a"}],
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
        utc_now_fn=lambda: "2026-02-24T00:00:00Z",
    )

    assert isinstance(payload, DashboardStatePayload)
    assert payload.generated_at == "2026-02-24T00:00:00Z"
    assert payload.summary["summary_ok"] is True
    assert payload.summary_error is None
    assert payload.traffic.recent_chat[0]["text"] == "hello"


def test_build_dashboard_state_handles_summary_builder_failure_without_crashing():
    tracker = _DummyTracker()
    payload = build_dashboard_state(
        iface=type("_Iface", (), {"myInfo": {}, "metadata": {}})(),
        tracker=tracker,
        started_at=0.0,
        target="target",
        show_secrets=True,
        storage_probe_path=".",
        revision_info={"version": "0.1.0", "commit": "abc"},
        sensitive_field_names={"password"},
        collect_nodes_fn=lambda iface: {
            "rows": [{"id": "!a"}],
            "full": [{"id": "!a", "info": {}}],
            "by_id": {"!a": {"id": "!a"}},
            "with_position_count": 1,
        },
        collect_local_state_fn=lambda iface: {},
        collect_local_state_safe_fn=lambda iface, *, collect_local_state_fn: ({}, None),
        modem_preset_from_local_state_fn=lambda state: None,
        apply_node_saved_counts_fn=lambda node_rows, saved_counts: None,
        build_summary_payload_fn=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("summary boom")),
        to_jsonable_fn=lambda value: value,
        redact_secrets_fn=lambda state, names: state,
        utc_now_fn=lambda: "2026-02-24T00:00:00Z",
    )

    assert payload["summary_error"] == "summary boom"
    assert payload["summary"]["target"] == "target"
    assert payload["summary"]["node_count"] == 1
    assert payload["summary"]["live_packet_count"] == 4


def test_build_dashboard_state_coerces_mapping_summary_payload_to_dict():
    tracker = _DummyTracker()
    payload = build_dashboard_state(
        iface=type("_Iface", (), {"myInfo": {}, "metadata": {}})(),
        tracker=tracker,
        started_at=0.0,
        target="target",
        show_secrets=True,
        storage_probe_path=".",
        revision_info={"version": "0.1.0"},
        sensitive_field_names={"password"},
        collect_nodes_fn=lambda iface: {
            "rows": [{"id": "!a"}],
            "full": [{"id": "!a", "info": {}}],
            "by_id": {"!a": {"id": "!a"}},
            "with_position_count": 1,
        },
        collect_local_state_fn=lambda iface: {},
        collect_local_state_safe_fn=lambda iface, *, collect_local_state_fn: ({}, None),
        modem_preset_from_local_state_fn=lambda state: None,
        apply_node_saved_counts_fn=lambda node_rows, saved_counts: None,
        build_summary_payload_fn=lambda **kwargs: MappingProxyType({"summary_ok": True}),
        to_jsonable_fn=lambda value: value,
        redact_secrets_fn=lambda state, names: state,
        utc_now_fn=lambda: "2026-02-24T00:00:00Z",
    )

    assert payload["summary"]["summary_ok"] is True
    assert payload["summary_error"] is None


def test_build_dashboard_state_coerces_mapping_local_state_and_preserves_error():
    tracker = _DummyTracker()
    payload = build_dashboard_state(
        iface=type("_Iface", (), {"myInfo": {}, "metadata": {}})(),
        tracker=tracker,
        started_at=0.0,
        target="target",
        show_secrets=True,
        storage_probe_path=".",
        revision_info={"version": "0.1.0"},
        sensitive_field_names={"password"},
        collect_nodes_fn=lambda iface: {
            "rows": [{"id": "!a"}],
            "full": [{"id": "!a", "info": {}}],
            "by_id": {"!a": {"id": "!a"}},
            "with_position_count": 1,
        },
        collect_local_state_fn=lambda iface: {},
        collect_local_state_safe_fn=lambda iface, *, collect_local_state_fn: (
            MappingProxyType({"local_config": {"lora": {"modem_preset": "LONG_FAST"}}}),
            "local warning",
        ),
        modem_preset_from_local_state_fn=lambda state: "LONG_FAST",
        apply_node_saved_counts_fn=lambda node_rows, saved_counts: None,
        build_summary_payload_fn=lambda **kwargs: {"modem_preset": kwargs["modem_preset"]},
        to_jsonable_fn=lambda value: value,
        redact_secrets_fn=lambda state, names: state,
        utc_now_fn=lambda: "2026-02-24T00:00:00Z",
    )

    assert isinstance(payload["local_state"], dict)
    assert payload["local_state"]["local_config"]["lora"]["modem_preset"] == "LONG_FAST"
    assert payload["local_state_error"] == "local warning"
    assert payload["summary"]["modem_preset"] == "LONG_FAST"


def test_build_dashboard_state_coerces_non_mapping_nested_saved_counts_to_empty_mapping():
    tracker = _DummyTracker()
    observed = {}
    payload = build_dashboard_state(
        iface=type("_Iface", (), {"myInfo": {}, "metadata": {}})(),
        tracker=tracker,
        started_at=0.0,
        target="target",
        show_secrets=True,
        storage_probe_path=".",
        revision_info={"version": "0.1.0"},
        sensitive_field_names={"password"},
        collect_nodes_fn=lambda iface: {
            "rows": [{"id": "!a"}],
            "full": [{"id": "!a", "info": {}}],
            "by_id": {"!a": {"id": "!a"}},
            "with_position_count": 1,
        },
        collect_local_state_fn=lambda iface: {},
        collect_local_state_safe_fn=lambda iface, *, collect_local_state_fn: ({}, None),
        modem_preset_from_local_state_fn=lambda state: None,
        apply_node_saved_counts_fn=lambda node_rows, node_saved_counts: observed.update(node_saved_counts),
        build_summary_payload_fn=lambda **kwargs: {"summary_ok": True},
        load_tracker_node_saved_counts_safe_fn=lambda tracker: ({"!a": "bad-shape"}, None),
        to_jsonable_fn=lambda value: value,
        redact_secrets_fn=lambda state, names: state,
        utc_now_fn=lambda: "2026-02-24T00:00:00Z",
    )

    assert observed["!a"] == {}
    assert payload["tracker_saved_counts_error"] is None


def test_build_dashboard_state_coerces_non_mapping_nested_capabilities_to_empty_mapping():
    tracker = _DummyTracker()
    payload = build_dashboard_state(
        iface=type("_Iface", (), {"myInfo": {}, "metadata": {}})(),
        tracker=tracker,
        started_at=0.0,
        target="target",
        show_secrets=True,
        storage_probe_path=".",
        revision_info={"version": "0.1.0"},
        sensitive_field_names={"password"},
        collect_nodes_fn=lambda iface: {
            "rows": [{"id": "!a"}],
            "full": [{"id": "!a", "info": {}}],
            "by_id": {"!a": {"id": "!a"}},
            "with_position_count": 1,
        },
        collect_local_state_fn=lambda iface: {},
        collect_local_state_safe_fn=lambda iface, *, collect_local_state_fn: ({}, None),
        modem_preset_from_local_state_fn=lambda state: None,
        apply_node_saved_counts_fn=lambda node_rows, saved_counts: None,
        build_summary_payload_fn=lambda **kwargs: {"summary_ok": True},
        load_tracker_node_capabilities_safe_fn=lambda tracker: ({"!a": "bad-shape"}, None),
        to_jsonable_fn=lambda value: value,
        redact_secrets_fn=lambda state, names: state,
        utc_now_fn=lambda: "2026-02-24T00:00:00Z",
    )

    assert payload["history_caps"]["!a"] == {}
    assert payload["tracker_capabilities_error"] is None
