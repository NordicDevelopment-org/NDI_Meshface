from typing import Protocol, cast


class PacketSender(Protocol):
    def _sendPacket(
        self,
        packet: object,
        *,
        destinationId: str,
        wantAck: bool,
    ) -> object:
        ...


def send_decoded_payload_packet(
    *,
    iface: object,
    destination_id: str,
    channel_index: int,
    portnum: int,
    payload: bytes,
    want_ack: bool,
    mesh_pb2_module: object,
    reply_id: int | None = None,
    emoji_codepoint: int | None = None,
) -> object:
    """Low-level send helper for decoded payload packets."""

    if mesh_pb2_module is None:
        raise RuntimeError("Meshtastic protobuf modules are unavailable for low-level sends")
    if not hasattr(iface, "_sendPacket"):
        raise RuntimeError("Meshtastic interface does not support low-level packet send")

    packet = mesh_pb2_module.MeshPacket()
    packet.channel = int(channel_index)
    packet.decoded.portnum = int(portnum)
    if reply_id is not None:
        packet.decoded.reply_id = int(reply_id)
    if emoji_codepoint is not None:
        packet.decoded.emoji = int(emoji_codepoint)
    packet.decoded.payload = bytes(payload or b"")
    sender = cast(PacketSender, iface)
    return sender._sendPacket(packet, destinationId=destination_id, wantAck=bool(want_ack))


def send_emoji_reaction_packet(
    *,
    iface: object,
    destination_id: str,
    channel_index: int,
    reply_id: int,
    emoji_codepoint: int,
    emoji_text: str,
    want_ack: bool,
    mesh_pb2_module: object,
    portnums_pb2_module: object,
) -> object:
    if mesh_pb2_module is None or portnums_pb2_module is None:
        raise RuntimeError("Meshtastic protobuf modules are unavailable for emoji reactions")
    return send_decoded_payload_packet(
        iface=iface,
        destination_id=destination_id,
        channel_index=channel_index,
        portnum=int(portnums_pb2_module.PortNum.TEXT_MESSAGE_APP),
        reply_id=int(reply_id),
        emoji_codepoint=int(emoji_codepoint),
        payload=str(emoji_text or "").encode("utf-8"),
        want_ack=want_ack,
        mesh_pb2_module=mesh_pb2_module,
    )
