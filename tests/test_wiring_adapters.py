from meshdash.wiring_adapters import (
    build_http_handler_factory,
    build_local_node_id_getter,
    build_reaction_sender,
    build_state_builder,
)


def test_build_state_builder_injects_sensitive_fields():
    captured = {}

    def _build_state_fn(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    state_builder = build_state_builder(
        build_state_fn=_build_state_fn,
        sensitive_field_names={"token"},
    )

    result = state_builder(iface="iface", tracker="tracker")

    assert result == {"ok": True}
    assert captured["sensitive_field_names"] == {"token"}
    assert captured["iface"] == "iface"


def test_build_reaction_sender_injects_protobuf_modules():
    captured = {}

    def _send_reaction(**kwargs):
        captured.update(kwargs)
        return {"sent": True}

    send_reaction = build_reaction_sender(
        send_emoji_reaction_packet_fn=_send_reaction,
        mesh_pb2_module="MESH_PB2",
        portnums_pb2_module="PORTNUMS_PB2",
    )
    result = send_reaction(destination_id="!abcd")

    assert result == {"sent": True}
    assert captured["mesh_pb2_module"] == "MESH_PB2"
    assert captured["portnums_pb2_module"] == "PORTNUMS_PB2"
    assert captured["destination_id"] == "!abcd"


def test_build_local_node_id_getter_injects_meshtastic_context():
    captured = {}

    def _get_local_node_id(iface, **kwargs):
        captured.update(kwargs)
        captured["iface"] = iface
        return "!abcd1234"

    get_local_node_id = build_local_node_id_getter(
        get_local_node_id_fn=_get_local_node_id,
        meshtastic_module="MESHTASTIC_MODULE",
        to_jsonable_fn=lambda value: value,
        to_int_fn=lambda value: value,
    )
    result = get_local_node_id("iface")

    assert result == "!abcd1234"
    assert captured["meshtastic_module"] == "MESHTASTIC_MODULE"
    assert captured["iface"] == "iface"


def test_build_http_handler_factory_injects_http_context():
    captured = {}

    def _make_http_handler(**kwargs):
        captured.update(kwargs)
        return object()

    make_http_handler = build_http_handler_factory(
        make_http_handler_fn=_make_http_handler,
        default_node_history_hours=72,
        to_int_fn=lambda value: value,
    )

    state_fn = lambda: {"ok": True}
    handler = make_http_handler("<html>", state_fn)

    assert handler is not None
    assert captured["html_text"] == "<html>"
    assert captured["state_fn"] is state_fn
    assert captured["default_node_history_hours"] == 72
    assert callable(captured["to_int_fn"])
