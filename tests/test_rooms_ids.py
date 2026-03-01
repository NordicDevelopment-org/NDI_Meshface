from meshdash.rooms.ids import normalize_room_id


def test_normalize_room_id_accepts_and_normalizes_valid_slugs():
    assert normalize_room_id("retro") == "retro"
    assert normalize_room_id(" Retro_ROOM-1 ") == "retro_room-1"
    assert normalize_room_id("a" * 48) == ("a" * 48)


def test_normalize_room_id_rejects_invalid_values():
    assert normalize_room_id(None) is None
    assert normalize_room_id("") is None
    assert normalize_room_id("_retro") is None
    assert normalize_room_id("-retro") is None
    assert normalize_room_id("room name") is None
    assert normalize_room_id("room!") is None
    assert normalize_room_id("a" * 49) is None
