from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re


ADVENTURE_DIR = Path(__file__).resolve().parent
DATA_PATH = ADVENTURE_DIR / "data" / "77-03-31_adventure.dat"


@dataclass(frozen=True)
class TravelOption:
    source: int
    destination: int
    words: tuple[int, ...]


@dataclass(frozen=True)
class AdventureWorld:
    long_descriptions: dict[int, str]
    short_descriptions: dict[int, str]
    travel: dict[int, tuple[TravelOption, ...]]
    vocabulary: dict[str, int]
    object_texts: dict[int, str]
    messages: dict[int, str]


def _compact(text: object) -> str:
    return " ".join(str(text or "").strip().split())


def _read_sections(path: Path) -> dict[int, list[str]]:
    sections: dict[int, list[str]] = {}
    current = 0
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        if stripped.isdigit():
            section = int(stripped)
            if section == 0:
                break
            current = section
            sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(line)
    return sections


def _parse_numbered_text(lines: list[str]) -> dict[int, str]:
    grouped: dict[int, list[str]] = {}
    for line in lines:
        if line.strip().startswith("-1"):
            break
        match = re.match(r"\s*(-?\d+)\s*(.*)$", line)
        if not match:
            continue
        key = int(match.group(1))
        if key < 0:
            break
        text = _compact(match.group(2))
        grouped.setdefault(key, [])
        if text and text.upper() != "END":
            grouped[key].append(text)
    return {key: _compact(" ".join(parts)) for key, parts in grouped.items()}


def _parse_travel(lines: list[str]) -> dict[int, tuple[TravelOption, ...]]:
    grouped: dict[int, list[TravelOption]] = {}
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("-1"):
            break
        values: list[int] = []
        for part in stripped.split():
            try:
                values.append(int(part))
            except Exception:
                values = []
                break
        if len(values) < 3:
            continue
        source, destination, *words = values
        option = TravelOption(
            source=source,
            destination=destination,
            words=tuple(word for word in words if word > 0),
        )
        grouped.setdefault(source, []).append(option)
    return {key: tuple(value) for key, value in grouped.items()}


def _parse_vocabulary(lines: list[str]) -> dict[str, int]:
    out: dict[str, int] = {}
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("-1"):
            break
        parts = stripped.split(None, 1)
        if len(parts) != 2:
            continue
        try:
            code = int(parts[0])
        except Exception:
            continue
        word = parts[1].strip().upper()
        if word:
            out[word[:5]] = code
    return out


@lru_cache(maxsize=1)
def load_adventure_world(path: Path = DATA_PATH) -> AdventureWorld:
    sections = _read_sections(path)
    return AdventureWorld(
        long_descriptions=_parse_numbered_text(sections.get(1, [])),
        short_descriptions=_parse_numbered_text(sections.get(2, [])),
        travel=_parse_travel(sections.get(3, [])),
        vocabulary=_parse_vocabulary(sections.get(4, [])),
        object_texts=_parse_numbered_text(sections.get(5, [])),
        messages=_parse_numbered_text(sections.get(6, [])),
    )


__all__ = [
    "AdventureWorld",
    "DATA_PATH",
    "TravelOption",
    "load_adventure_world",
]
