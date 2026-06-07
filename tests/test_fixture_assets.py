from pathlib import Path
import struct


def test_file_transfer_64k_fixture_is_exact_size_png() -> None:
    fixture = Path(__file__).resolve().parent / "fixtures" / "file_transfer_64k.png"
    data = fixture.read_bytes()

    assert len(data) == 64 * 1024
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert data[12:16] == b"IHDR"

    width, height, bit_depth, color_type = struct.unpack(">IIBB", data[16:26])
    assert (width, height) == (128, 128)
    assert bit_depth == 8
    assert color_type == 2
