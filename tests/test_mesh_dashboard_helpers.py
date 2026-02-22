from meshdash.helpers import (
    calculate_hops,
    disk_space_info,
    emoji_from_codepoint,
    extract_emoji_codepoint,
    extract_reply_id,
    format_epoch,
    normalize_single_emoji,
    to_int,
)


def test_to_int_handles_valid_and_invalid_values():
    assert to_int("42") == 42
    assert to_int(7.0) == 7
    assert to_int(None) is None
    assert to_int("not-a-number") is None


def test_format_epoch_returns_utc_string():
    assert format_epoch(1) == "1970-01-01 00:00:01Z"
    assert format_epoch(0) is None
    assert format_epoch("bad") is None


def test_calculate_hops_only_when_non_negative():
    assert calculate_hops(4, 2) == 2
    assert calculate_hops(2, 4) is None
    assert calculate_hops(None, 1) is None


def test_extract_reply_id_accepts_both_key_styles():
    assert extract_reply_id({"replyId": 123}) == 123
    assert extract_reply_id({"reply_id": "456"}) == 456
    assert extract_reply_id({"replyId": 0}) is None
    assert extract_reply_id({"other": 99}) is None


def test_extract_emoji_codepoint_accepts_int_string_and_glyph():
    assert extract_emoji_codepoint({"emoji": 128077}) == 128077
    assert extract_emoji_codepoint({"emoji": "128077"}) == 128077
    assert extract_emoji_codepoint({"emoji": "👍"}) == ord("👍")
    assert extract_emoji_codepoint({"emoji": ""}) is None
    assert extract_emoji_codepoint({"emoji": 0}) is None


def test_emoji_helpers_round_trip_simple_emoji():
    glyph, codepoint = normalize_single_emoji("👍")
    assert glyph == "👍"
    assert codepoint == ord("👍")
    assert emoji_from_codepoint(codepoint) == "👍"


def test_normalize_single_emoji_accepts_codepoint_string():
    glyph, codepoint = normalize_single_emoji(str(ord("😀")))
    assert glyph == "😀"
    assert codepoint == ord("😀")


def test_disk_space_info_has_expected_shape_for_current_dir():
    info = disk_space_info(".")
    assert isinstance(info, dict)
    assert "path" in info
    assert any(key in info for key in ("free_bytes", "error"))
