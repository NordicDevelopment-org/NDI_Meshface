from typing import Any


def append_local_chat_entry(
    *,
    recent_chat: Any,
    history_store: Any,
    entry: Any,
) -> bool:
    if entry is None:
        return False
    recent_chat.append(entry)
    if history_store is not None:
        history_store.save_chat(entry)
    return True
