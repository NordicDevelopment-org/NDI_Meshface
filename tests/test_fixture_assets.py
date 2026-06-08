from pathlib import Path
import binascii
import gzip
import struct

import pytest


@pytest.mark.parametrize("kib", [1, 2, 4, 8, 16, 32, 64])
def test_file_transfer_fixture_is_labeled_compression_resistant_png(kib: int) -> None:
    fixture = (
        Path(__file__).resolve().parent
        / "fixtures"
        / f"file_transfer_{kib}k.png"
    )
    data = fixture.read_bytes()

    requested_size = kib * 1024
    assert requested_size * 0.85 <= len(data) <= requested_size * 1.20
    assert data.startswith(b"\x89PNG\r\n\x1a\n")

    chunks = _png_chunks(data)
    assert chunks[0][0] == b"IHDR"
    width, height, bit_depth, color_type = struct.unpack(">IIBB", data[16:26])
    assert (width, height) == (128, 128)
    assert bit_depth == 8
    assert color_type == 3

    text_chunks = [payload for kind, payload in chunks if kind == b"tEXt"]
    label = f"Meshyface test file fixture; requested size ~{kib} KiB".encode(
        "latin-1"
    )
    assert any(label in payload for payload in text_chunks)
    assert any(kind == b"raNd" and payload for kind, payload in chunks)

    gzip_size = len(gzip.compress(data, compresslevel=9))
    assert gzip_size >= int(len(data) * 0.80)


def _png_chunks(data: bytes) -> list[tuple[bytes, bytes]]:
    chunks: list[tuple[bytes, bytes]] = []
    offset = 8
    while offset < len(data):
        assert offset + 12 <= len(data)
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        payload_start = offset + 8
        payload_end = payload_start + length
        crc_end = payload_end + 4
        assert crc_end <= len(data)
        payload = data[payload_start:payload_end]
        observed_crc = struct.unpack(">I", data[payload_end:crc_end])[0]
        expected_crc = binascii.crc32(kind)
        expected_crc = binascii.crc32(payload, expected_crc) & 0xFFFFFFFF
        assert observed_crc == expected_crc
        chunks.append((kind, payload))
        offset = crc_end
        if kind == b"IEND":
            break
    assert offset == len(data)
    assert chunks[-1][0] == b"IEND"
    return chunks
