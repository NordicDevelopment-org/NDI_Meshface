RECENT_CHAT_BUFFER_MULTIPLIER = 4
MAX_RECENT_CHAT_BUFFER = 5000


def recent_chat_buffer_limit(packet_limit: int) -> int:
    clean_limit = max(1, int(packet_limit))
    return min(MAX_RECENT_CHAT_BUFFER, clean_limit * RECENT_CHAT_BUFFER_MULTIPLIER)
