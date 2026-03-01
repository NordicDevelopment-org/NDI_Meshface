import types

import pytest

from meshdash.mesh_ops import (
    get_local_node_id,
    send_decoded_payload_packet,
    send_emoji_reaction_packet,
)


def test_get_local_node_id_uses_meshtastic_broadcast_num():
    fake_meshtastic = types.SimpleNamespace(BROADCAST_NUM=0xFFFFFFFF)

    class _Iface:
        myInfo = {"my_node_num": 0x12345678}

    node_id = get_local_node_id(
        _Iface(),
        meshtastic_module=fake_meshtastic,
        to_jsonable_fn=lambda value: value,
        to_int_fn=lambda value: int(value) if value is not None else None,
    )
    assert node_id == "!12345678"


def test_send_emoji_reaction_packet_requires_proto_modules():
    iface = types.SimpleNamespace(_sendPacket=lambda *args, **kwargs: None)
    with pytest.raises(RuntimeError, match="protobuf"):
        send_emoji_reaction_packet(
            iface=iface,
            destination_id="!abc",
            channel_index=1,
            reply_id=2,
            emoji_codepoint=128512,
            emoji_text="😀",
            want_ack=False,
            mesh_pb2_module=None,
            portnums_pb2_module=None,
        )


def test_send_emoji_reaction_packet_builds_packet_and_sends():
    calls = []

    class _Decoded:
        def __init__(self):
            self.portnum = None
            self.reply_id = None
            self.emoji = None
            self.payload = b""

    class _Packet:
        def __init__(self):
            self.channel = 0
            self.decoded = _Decoded()

    class _MeshPB2:
        MeshPacket = _Packet

    class _PortNums:
        class PortNum:
            TEXT_MESSAGE_APP = 123

    class _Iface:
        def _sendPacket(self, packet, destinationId, wantAck):
            calls.append((packet, destinationId, wantAck))
            return {"ok": True}

    out = send_emoji_reaction_packet(
        iface=_Iface(),
        destination_id="!abc",
        channel_index=3,
        reply_id=99,
        emoji_codepoint=128512,
        emoji_text="😀",
        want_ack=True,
        mesh_pb2_module=_MeshPB2,
        portnums_pb2_module=_PortNums,
    )

    assert out == {"ok": True}
    packet, destination, want_ack = calls[0]
    assert destination == "!abc"
    assert want_ack is True
    assert packet.channel == 3
    assert packet.decoded.portnum == 123
    assert packet.decoded.reply_id == 99
    assert packet.decoded.emoji == 128512
    assert packet.decoded.payload == "😀".encode("utf-8")


def test_send_decoded_payload_packet_requires_mesh_pb2():
    iface = types.SimpleNamespace(_sendPacket=lambda *args, **kwargs: None)
    with pytest.raises(RuntimeError, match="protobuf"):
        send_decoded_payload_packet(
            iface=iface,
            destination_id="!abc",
            channel_index=1,
            portnum=257,
            payload=b"hello",
            want_ack=False,
            mesh_pb2_module=None,
        )


def test_send_decoded_payload_packet_requires_low_level_sender():
    class _Decoded:
        def __init__(self):
            self.portnum = None
            self.reply_id = None
            self.emoji = None
            self.payload = b""

    class _Packet:
        def __init__(self):
            self.channel = 0
            self.decoded = _Decoded()

    class _MeshPB2:
        MeshPacket = _Packet

    with pytest.raises(RuntimeError, match="low-level"):
        send_decoded_payload_packet(
            iface=object(),
            destination_id="!abc",
            channel_index=1,
            portnum=257,
            payload=b"hello",
            want_ack=False,
            mesh_pb2_module=_MeshPB2,
        )


def test_send_decoded_payload_packet_builds_packet_and_sends():
    calls = []

    class _Decoded:
        def __init__(self):
            self.portnum = None
            self.reply_id = None
            self.emoji = None
            self.payload = b""

    class _Packet:
        def __init__(self):
            self.channel = 0
            self.decoded = _Decoded()

    class _MeshPB2:
        MeshPacket = _Packet

    class _Iface:
        def _sendPacket(self, packet, destinationId, wantAck):
            calls.append((packet, destinationId, wantAck))
            return {"ok": True}

    out = send_decoded_payload_packet(
        iface=_Iface(),
        destination_id="^all",
        channel_index=2,
        portnum=257,
        payload=b"room-bytes",
        want_ack=False,
        mesh_pb2_module=_MeshPB2,
        reply_id=44,
        emoji_codepoint=128512,
    )

    assert out == {"ok": True}
    packet, destination, want_ack = calls[0]
    assert destination == "^all"
    assert want_ack is False
    assert packet.channel == 2
    assert packet.decoded.portnum == 257
    assert packet.decoded.reply_id == 44
    assert packet.decoded.emoji == 128512
    assert packet.decoded.payload == b"room-bytes"
