import base64
import re
import urllib.parse


FILE_TRANSFER_PROTOCOL_NAME = "MF_FILE_V1"
FILE_TRANSFER_PROTOCOL_PREFIX = f"{FILE_TRANSFER_PROTOCOL_NAME}|"
_FILE_TRANSFER_FRAME_TYPES = {"M", "C", "A", "F"}
_TRANSFER_ID_RE = re.compile(r"^[a-z0-9]{4,24}$")


def is_file_transfer_protocol_text(text: object) -> bool:
    if not isinstance(text, str):
        return False
    raw = text.strip()
    if not raw.startswith(FILE_TRANSFER_PROTOCOL_PREFIX):
        return False
    parts = raw.split("|", 3)
    if len(parts) < 3:
        return False
    frame_type = str(parts[1]).strip().upper()
    transfer_id = str(parts[2]).strip()
    return frame_type in _FILE_TRANSFER_FRAME_TYPES and bool(transfer_id)


def is_file_transfer_protocol_chat_entry(entry: object) -> bool:
    if not isinstance(entry, dict):
        return False
    return is_file_transfer_protocol_text(entry.get("text"))


def _safe_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except Exception:
        return None


def parse_file_transfer_frame_text(text: object) -> dict[str, object] | None:
    raw = str(text or "").strip()
    if not raw.startswith(FILE_TRANSFER_PROTOCOL_PREFIX):
        return None
    parts = raw.split("|")
    if len(parts) < 4:
        return None
    frame_type = str(parts[1] or "").strip().upper()
    transfer_id = str(parts[2] or "").strip().lower()
    if not _TRANSFER_ID_RE.fullmatch(transfer_id):
        return None

    if frame_type == "M":
        if len(parts) < 6:
            return None
        file_size = _safe_int(parts[4])
        total_chunks = _safe_int(parts[5])
        if file_size is None or file_size < 0:
            return None
        if total_chunks is None or total_chunks <= 0:
            return None
        codec = str(parts[6] if len(parts) >= 7 else "raw").strip().lower() or "raw"
        original_size = _safe_int(parts[7] if len(parts) >= 8 else file_size)
        return {
            "kind": "meta",
            "transfer_id": transfer_id,
            "file_name": urllib.parse.unquote(str(parts[3] or "").strip()),
            "file_size": int(file_size),
            "total_chunks": int(total_chunks),
            "codec": codec,
            "original_file_size": int(
                original_size
                if original_size is not None and original_size >= 0
                else file_size
            ),
        }

    if frame_type == "C":
        if len(parts) < 5:
            return None
        chunk_index = _safe_int(parts[3])
        chunk_data = str(parts[4] or "").strip()
        if chunk_index is None or chunk_index < 0:
            return None
        if not chunk_data or not re.fullmatch(r"[A-Za-z0-9+/=]+", chunk_data):
            return None
        return {
            "kind": "chunk",
            "transfer_id": transfer_id,
            "chunk_index": int(chunk_index),
            "chunk_data": chunk_data,
        }

    if frame_type == "A":
        if len(parts) < 6:
            return None
        received_count = _safe_int(parts[3])
        total_chunks = _safe_int(parts[4])
        bitmap = str(parts[5] or "").strip()
        if received_count is None or received_count < 0:
            return None
        if total_chunks is None or total_chunks <= 0:
            return None
        if not bitmap or not re.fullmatch(r"[A-Za-z0-9+/=]+", bitmap):
            return None
        return {
            "kind": "ack",
            "transfer_id": transfer_id,
            "received_count": min(int(received_count), int(total_chunks)),
            "total_chunks": int(total_chunks),
            "bitmap": bitmap,
        }

    if frame_type == "F":
        action_code = str(parts[3] or "").strip().upper()
        action = {"P": "pause", "R": "resume", "X": "cancel"}.get(action_code, "")
        if not action:
            return None
        return {
            "kind": "flow",
            "transfer_id": transfer_id,
            "action": action,
        }

    return None


def build_file_transfer_ack_frame(
    *,
    transfer_id: object,
    total_chunks: object,
    received_indexes: object = None,
) -> str:
    clean_id = str(transfer_id or "").strip().lower()
    if not _TRANSFER_ID_RE.fullmatch(clean_id):
        return ""
    parsed_total = _safe_int(total_chunks)
    total = max(1, int(parsed_total if parsed_total is not None else 1))
    source = received_indexes if received_indexes is not None else ()
    indexes: set[int] = set()
    try:
        iterator = iter(source)  # type: ignore[arg-type]
    except Exception:
        iterator = iter(())
    for idx_raw in iterator:
        idx = _safe_int(idx_raw)
        if idx is None or idx < 0 or idx >= total:
            continue
        indexes.add(int(idx))
    if len(indexes) >= total:
        # The count is authoritative for completion. Keep the final ACK small enough
        # to fit in one chat frame even for transfers with many chunks.
        bitmap = bytearray(1)
    else:
        max_index = max(indexes) if indexes else 0
        byte_len = max(1, (max_index // 8) + 1)
        bitmap = bytearray(byte_len)
        for idx in indexes:
            bitmap[idx // 8] |= 1 << (idx % 8)
    encoded = base64.b64encode(bytes(bitmap)).decode("ascii")
    return f"{FILE_TRANSFER_PROTOCOL_NAME}|A|{clean_id}|{len(indexes)}|{total}|{encoded}"


__all__ = [
    "FILE_TRANSFER_PROTOCOL_NAME",
    "FILE_TRANSFER_PROTOCOL_PREFIX",
    "build_file_transfer_ack_frame",
    "is_file_transfer_protocol_chat_entry",
    "is_file_transfer_protocol_text",
    "parse_file_transfer_frame_text",
]
