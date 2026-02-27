from typing import Protocol, cast

from .nodes import get_local_node_id as _get_local_node_id_helper
from .runtime_types import ToIntFn, ToJsonableFn


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
    """Low-level send helper for decoded payload packets.

    Meshyface uses this primitive to implement features that don't map cleanly
    onto the high-level Meshtastic python API (e.g. reactions, Rooms sideband).

    Args:
        iface: Meshtastic interface instance.
        destination_id: "^all" or a node id like "!abcdef12".
        channel_index: Meshtastic channel index to transmit on.
        portnum: numeric port number (protobuf enum value).
        payload: raw decoded payload bytes.
        want_ack: request ACK for direct messages.
        mesh_pb2_module: meshtastic.protobuf.mesh_pb2 module.
        reply_id: optional packet id being replied to.
        emoji_codepoint: optional emoji codepoint for reactions.
    """

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


def get_local_node_id(
    iface: object,
    *,
    meshtastic_module: object,
    to_jsonable_fn: ToJsonableFn,
    to_int_fn: ToIntFn,
) -> str:
    broadcast_num = (
        getattr(meshtastic_module, "BROADCAST_NUM", None)
        if meshtastic_module is not None
        else None
    )
    return _get_local_node_id_helper(
        iface,
        broadcast_num=broadcast_num,
        to_jsonable_fn=to_jsonable_fn,
        to_int_fn=to_int_fn,
    )


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
