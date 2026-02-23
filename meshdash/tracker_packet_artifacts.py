from typing import Any, Dict, Optional, Tuple


def build_tracker_packet_artifacts(
    *,
    packet: Dict[str, Any],
    parsed: Dict[str, Any],
    include_live_count: bool,
    build_packet_summary_fn,
    build_chat_entry_from_packet_fn,
    utc_now_fn,
    format_epoch_fn,
    to_int_fn,
    to_jsonable_fn,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    packet_summary = build_packet_summary_fn(
        packet=packet,
        decoded=parsed["decoded"],
        from_id=parsed["from_id"],
        to_id=parsed["to_id"],
        packet_id=parsed["packet_id"],
        rx_time=parsed["rx_time"],
        hops=parsed["hops"],
        reply_id=parsed["reply_id"],
        emoji_glyph=parsed["emoji_glyph"],
        emoji_codepoint=parsed["emoji_codepoint"],
        is_reaction=parsed["is_reaction"],
        packet_position=parsed["packet_position"],
        packet_battery=parsed["packet_battery"],
        utc_now_fn=utc_now_fn,
        format_epoch_fn=format_epoch_fn,
        to_int_fn=to_int_fn,
    )
    packet_summary["live"] = include_live_count

    packet_entry = {
        "summary": packet_summary,
        "packet": to_jsonable_fn(packet),
    }

    chat_entry = build_chat_entry_from_packet_fn(
        packet=packet,
        decoded=parsed["decoded"],
        from_id=parsed["from_id"],
        to_id=parsed["to_id"],
        packet_id=parsed["packet_id"],
        hops=parsed["hops"],
        reply_id=parsed["reply_id"],
        emoji_glyph=parsed["emoji_glyph"],
        emoji_codepoint=parsed["emoji_codepoint"],
        is_reaction=parsed["is_reaction"],
        utc_now_fn=utc_now_fn,
        format_epoch_fn=format_epoch_fn,
    )
    return packet_entry, chat_entry
