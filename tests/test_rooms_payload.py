import pytest

from meshdash.rooms.payload import RoomMessage, encode_room_message, try_decode_room_message


def test_try_decode_room_message_returns_none_for_placeholder_decoder():
    assert try_decode_room_message(b"") is None
    assert try_decode_room_message(b"room payload bytes") is None


def test_encode_room_message_rejects_invalid_room_id():
    with pytest.raises(ValueError, match="Invalid room id"):
        encode_room_message(RoomMessage(room_id="bad room", text="hello"))


def test_encode_room_message_raises_not_implemented_for_valid_room():
    with pytest.raises(NotImplementedError, match="not implemented"):
        encode_room_message(RoomMessage(room_id="retro", text="hello"))
