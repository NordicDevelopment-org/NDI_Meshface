#!/usr/bin/env python3
"""Generate deterministic PNG fixtures for manual file-transfer testing."""

from __future__ import annotations

import binascii
import hashlib
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures"
KIB_VALUES = (1, 2, 4, 8, 16, 32, 64)
WIDTH = 128
HEIGHT = 128
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

PALETTE = (
    (18, 24, 31),
    (29, 43, 61),
    (39, 70, 84),
    (71, 112, 91),
    (188, 210, 129),
    (238, 242, 220),
    (9, 13, 20),
    (214, 103, 71),
)

FONT = {
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "~": ("00000", "01010", "10100", "00000", "00000", "00000", "00000"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
}


def _chunk(kind: bytes, payload: bytes) -> bytes:
    crc = binascii.crc32(kind)
    crc = binascii.crc32(payload, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)


def _deterministic_bytes(seed: str, size: int) -> bytes:
    output = bytearray()
    counter = 0
    while len(output) < size:
        block_seed = f"{seed}:{counter}".encode("ascii")
        output.extend(hashlib.sha256(block_seed).digest())
        counter += 1
    return bytes(output[:size])


def _draw_rect(pixels: bytearray, x0: int, y0: int, x1: int, y1: int, color: int) -> None:
    for y in range(max(0, y0), min(HEIGHT, y1)):
        row = y * WIDTH
        for x in range(max(0, x0), min(WIDTH, x1)):
            pixels[row + x] = color


def _draw_text(
    pixels: bytearray,
    text: str,
    *,
    x: int,
    y: int,
    color: int,
    scale: int = 2,
) -> None:
    cursor = x
    for char in text.upper():
        glyph = FONT.get(char)
        if glyph is None:
            cursor += 6 * scale
            continue
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit != "1":
                    continue
                _draw_rect(
                    pixels,
                    cursor + gx * scale,
                    y + gy * scale,
                    cursor + (gx + 1) * scale,
                    y + (gy + 1) * scale,
                    color,
                )
        cursor += 6 * scale


def _text_width(text: str, scale: int = 2) -> int:
    return max(0, len(text) * 6 * scale - scale)


def _render_pixels(kib: int) -> bytearray:
    pixels = bytearray(WIDTH * HEIGHT)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            value = ((x * 17) ^ (y * 29) ^ (kib * 43) ^ ((x * y) >> 2)) & 0xFF
            pixels[y * WIDTH + x] = 1 + (value % 4)

    _draw_rect(pixels, 8, 22, 120, 87, 6)
    _draw_rect(pixels, 10, 24, 118, 85, 0)
    _draw_rect(pixels, 10, 24, 118, 29, 7)
    _draw_rect(pixels, 10, 80, 118, 85, 2)

    line1 = "TEST FILE"
    line2 = f"~{kib} KIB"
    _draw_text(
        pixels,
        line1,
        x=(WIDTH - _text_width(line1)) // 2,
        y=39,
        color=5,
    )
    _draw_text(
        pixels,
        line2,
        x=(WIDTH - _text_width(line2)) // 2,
        y=60,
        color=4,
    )
    return pixels


def _base_png_without_entropy(kib: int) -> bytes:
    pixels = _render_pixels(kib)
    scanlines = bytearray()
    for y in range(HEIGHT):
        scanlines.append(0)
        start = y * WIDTH
        scanlines.extend(pixels[start : start + WIDTH])

    ihdr = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 3, 0, 0, 0)
    palette = bytes(channel for color in PALETTE for channel in color)
    text = (
        f"Description\x00Meshyface test file fixture; requested size ~{kib} KiB; "
        "contains deterministic high-entropy padding for transfer tests"
    ).encode("latin-1")
    idat = zlib.compress(bytes(scanlines), level=9)

    return b"".join(
        (
            PNG_SIGNATURE,
            _chunk(b"IHDR", ihdr),
            _chunk(b"PLTE", palette),
            _chunk(b"tEXt", text),
            _chunk(b"IDAT", idat),
        )
    )


def build_fixture_png(kib: int) -> bytes:
    base = _base_png_without_entropy(kib)
    iend = _chunk(b"IEND", b"")
    target_size = (kib * 1024) + (37 if kib < 64 else -37)
    entropy_len = max(0, target_size - len(base) - len(iend) - 12)
    entropy = _chunk(b"raNd", _deterministic_bytes(f"file-transfer-{kib}k", entropy_len))
    return base + entropy + iend


def main() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    for kib in KIB_VALUES:
        path = FIXTURE_DIR / f"file_transfer_{kib}k.png"
        path.write_bytes(build_fixture_png(kib))
        print(f"{path.relative_to(ROOT)} {path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
