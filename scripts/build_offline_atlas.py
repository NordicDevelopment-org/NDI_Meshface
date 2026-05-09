#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import struct
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_ATLAS = ROOT / "meshdash" / "assets" / "offline_atlas_na.min.json"
DEFAULT_OUTPUT = DEFAULT_BASE_ATLAS
MAX_ATLAS_BYTES = 5 * 1024 * 1024

NATURAL_EARTH_ZIPS = {
    "countries": (
        "ne_110m_admin_0_countries.zip",
        "https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip",
    ),
    "coastline": (
        "ne_110m_coastline.zip",
        "https://naturalearth.s3.amazonaws.com/110m_physical/ne_110m_coastline.zip",
    ),
    "borders": (
        "ne_110m_admin_0_boundary_lines_land.zip",
        "https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_boundary_lines_land.zip",
    ),
    "cities": (
        "ne_110m_populated_places.zip",
        "https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_populated_places.zip",
    ),
    "lakes": (
        "ne_110m_lakes.zip",
        "https://naturalearth.s3.amazonaws.com/110m_physical/ne_110m_lakes.zip",
    ),
    "rivers": (
        "ne_110m_rivers_lake_centerlines.zip",
        "https://naturalearth.s3.amazonaws.com/110m_physical/ne_110m_rivers_lake_centerlines.zip",
    ),
}

NA_DETAIL_BBOX = (-170.0, 15.0, -50.0, 75.0)


def _round_coord(value: float) -> float:
    rounded = round(float(value), 4)
    if rounded == 0:
        return 0.0
    return rounded


def _parse_dbf(raw: bytes) -> list[dict[str, Any]]:
    record_count = struct.unpack("<I", raw[4:8])[0]
    header_len = struct.unpack("<H", raw[8:10])[0]
    record_len = struct.unpack("<H", raw[10:12])[0]
    fields: list[tuple[str, str, int]] = []
    offset = 32
    while offset < header_len and raw[offset] != 0x0D:
        desc = raw[offset : offset + 32]
        name = desc[:11].split(b"\0", 1)[0].decode("latin-1").strip()
        fields.append((name, chr(desc[11]), int(desc[16])))
        offset += 32

    records: list[dict[str, Any]] = []
    cursor = header_len
    for _ in range(record_count):
        row = raw[cursor : cursor + record_len]
        cursor += record_len
        if not row or row[0:1] == b"*":
            continue
        values: dict[str, Any] = {}
        field_offset = 1
        for name, field_type, field_len in fields:
            chunk = row[field_offset : field_offset + field_len]
            field_offset += field_len
            text = chunk.split(b"\0", 1)[0].decode("latin-1", errors="ignore").strip()
            if field_type in {"N", "F"}:
                if text:
                    try:
                        parsed = float(text)
                        values[name] = int(parsed) if parsed.is_integer() else parsed
                    except ValueError:
                        values[name] = text
                else:
                    values[name] = None
            else:
                values[name] = text
        records.append(values)
    return records


def _split_parts(points: list[list[float]], parts: list[int]) -> list[list[list[float]]]:
    boundaries = parts + [len(points)]
    return [points[boundaries[i] : boundaries[i + 1]] for i in range(len(parts))]


def _parse_shp(raw: bytes) -> list[dict[str, Any]]:
    geometries: list[dict[str, Any]] = []
    offset = 100
    while offset + 8 <= len(raw):
        content_len = struct.unpack(">i", raw[offset + 4 : offset + 8])[0] * 2
        content = raw[offset + 8 : offset + 8 + content_len]
        offset += 8 + content_len
        if len(content) < 4:
            continue
        shape_type = struct.unpack("<i", content[:4])[0]
        if shape_type == 0:
            continue
        if shape_type == 1:
            lon, lat = struct.unpack("<dd", content[4:20])
            geometries.append({"type": "Point", "coordinates": [_round_coord(lon), _round_coord(lat)]})
            continue
        if shape_type not in {3, 5} or len(content) < 44:
            continue
        num_parts, num_points = struct.unpack("<ii", content[36:44])
        parts_offset = 44
        points_offset = parts_offset + (num_parts * 4)
        parts = list(struct.unpack(f"<{num_parts}i", content[parts_offset:points_offset]))
        point_values = struct.unpack(f"<{num_points * 2}d", content[points_offset : points_offset + (num_points * 16)])
        points = [
            [_round_coord(point_values[i]), _round_coord(point_values[i + 1])]
            for i in range(0, len(point_values), 2)
        ]
        split = [part for part in _split_parts(points, parts) if len(part) >= 2]
        if shape_type == 3:
            if len(split) == 1:
                geometries.append({"type": "LineString", "coordinates": split[0]})
            else:
                geometries.append({"type": "MultiLineString", "coordinates": split})
            continue
        polygons = [[ring] for ring in split if len(ring) >= 4]
        if len(polygons) == 1:
            geometries.append({"type": "Polygon", "coordinates": polygons[0]})
        elif polygons:
            geometries.append({"type": "MultiPolygon", "coordinates": polygons})
    return geometries


def _zip_members(path: Path) -> tuple[bytes, bytes]:
    with ZipFile(path) as archive:
        shp_name = next(name for name in archive.namelist() if name.lower().endswith(".shp"))
        dbf_name = next(name for name in archive.namelist() if name.lower().endswith(".dbf"))
        return archive.read(shp_name), archive.read(dbf_name)


def _features_from_zip(path: Path, property_builder) -> list[dict[str, Any]]:
    shp_raw, dbf_raw = _zip_members(path)
    geometries = _parse_shp(shp_raw)
    records = _parse_dbf(dbf_raw)
    features: list[dict[str, Any]] = []
    for geometry, record in zip(geometries, records):
        props = property_builder(record)
        if props is None:
            continue
        features.append({"type": "Feature", "properties": props, "geometry": geometry})
    return features


def _collection(features: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": features}


def _text(record: dict[str, Any], *names: str) -> str:
    for name in names:
        value = str(record.get(name) or "").strip()
        if value:
            return value
    return ""


def _number(record: dict[str, Any], name: str, fallback: float = 0.0) -> float:
    value = record.get(name)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return number if math.isfinite(number) else fallback


def _natural_earth_city_rank(record: dict[str, Any]) -> int:
    population = _number(record, "POP_MAX", 0)
    is_capital = _number(record, "ADM0CAP", 0) >= 1
    is_world_city = _number(record, "WORLDCITY", 0) >= 1 or _number(record, "MEGACITY", 0) >= 1
    if population >= 15_000_000:
        return 0
    if population >= 6_000_000 or is_world_city:
        return 1
    if population >= 1_000_000 or is_capital:
        return 2
    return 3


def _geometry_points(geometry: dict[str, Any]):
    gtype = geometry.get("type")
    coords = geometry.get("coordinates")
    if gtype == "Point":
        yield coords
    elif gtype in {"LineString", "MultiPoint"}:
        yield from coords
    elif gtype in {"Polygon", "MultiLineString"}:
        for line in coords:
            yield from line
    elif gtype == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                yield from ring


def _feature_bbox(feature: dict[str, Any]) -> tuple[float, float, float, float] | None:
    xs: list[float] = []
    ys: list[float] = []
    for point in _geometry_points(feature.get("geometry") or {}):
        if isinstance(point, list) and len(point) >= 2:
            xs.append(float(point[0]))
            ys.append(float(point[1]))
    if not xs or not ys:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def _bbox_center_inside(bbox: tuple[float, float, float, float], outer: tuple[float, float, float, float]) -> bool:
    west, south, east, north = bbox
    outer_west, outer_south, outer_east, outer_north = outer
    center_lon = (west + east) * 0.5
    center_lat = (south + north) * 0.5
    return outer_west <= center_lon <= outer_east and outer_south <= center_lat <= outer_north


def _outside_na_detail(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for feature in features:
        bbox = _feature_bbox(feature)
        if bbox is None or not _bbox_center_inside(bbox, NA_DETAIL_BBOX):
            kept.append(feature)
    return kept


def _inside_na_detail(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for feature in features:
        bbox = _feature_bbox(feature)
        if bbox is not None and _bbox_center_inside(bbox, NA_DETAIL_BBOX):
            kept.append(feature)
    return kept


def _natural_earth_city_feature(feature: dict[str, Any]) -> dict[str, Any] | None:
    props = feature.get("properties") or {}
    country = str(props.get("adm0name") or "").strip()
    if country == "United States of America":
        return None
    geometry = feature.get("geometry")
    if not isinstance(geometry, dict) or geometry.get("type") != "Point":
        return None
    name = str(props.get("name") or "").strip()
    if not name:
        return None
    return {
        "type": "Feature",
        "properties": props,
        "geometry": geometry,
    }


def _dedupe_point_features(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, float, float]] = set()
    kept: list[dict[str, Any]] = []
    for feature in features:
        props = feature.get("properties") or {}
        coords = (feature.get("geometry") or {}).get("coordinates")
        if not isinstance(coords, list) or len(coords) < 2:
            continue
        key = (
            str(props.get("name") or "").strip().casefold(),
            round(float(coords[0]), 2),
            round(float(coords[1]), 2),
        )
        if key in seen:
            continue
        seen.add(key)
        kept.append(feature)
    return kept


def _download_sources(source_dir: Path) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    for filename, url in NATURAL_EARTH_ZIPS.values():
        target = source_dir / filename
        if target.exists() and target.stat().st_size > 0:
            continue
        print(f"Downloading {url}")
        urllib.request.urlretrieve(url, target)


def _source_path(source_dir: Path, key: str) -> Path:
    filename, _url = NATURAL_EARTH_ZIPS[key]
    path = source_dir / filename
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def build_atlas(base_atlas: Path, source_dir: Path) -> dict[str, Any]:
    payload = json.loads(base_atlas.read_text(encoding="utf-8"))
    layers = payload.get("layers")
    if not isinstance(layers, dict):
        raise ValueError("base atlas has no layers object")

    countries = _features_from_zip(
        _source_path(source_dir, "countries"),
        lambda row: {
            "name": _text(row, "NAME", "ADMIN"),
            "iso_a2": _text(row, "ISO_A2", "POSTAL"),
            "iso_a3": _text(row, "ISO_A3", "ADM0_A3"),
        },
    )
    coastline = _features_from_zip(
        _source_path(source_dir, "coastline"),
        lambda row: {"scalerank": _number(row, "scalerank", 0)},
    )
    borders = _features_from_zip(
        _source_path(source_dir, "borders"),
        lambda row: {"name": _text(row, "NAME"), "scalerank": _number(row, "SCALERANK", 0)},
    )
    global_lakes = _features_from_zip(
        _source_path(source_dir, "lakes"),
        lambda row: {"name": _text(row, "name", "label"), "scalerank": _number(row, "scalerank", 9)},
    )
    global_rivers = _features_from_zip(
        _source_path(source_dir, "rivers"),
        lambda row: {"name": _text(row, "name", "label"), "scalerank": _number(row, "scalerank", 9)},
    )
    global_cities_raw = _features_from_zip(
        _source_path(source_dir, "cities"),
        lambda row: {
            "name": _text(row, "NAMEASCII", "NAME"),
            "scalerank": _natural_earth_city_rank(row),
            "population": _number(row, "POP_MAX", 0),
            "adm0name": _text(row, "ADM0NAME", "SOV0NAME"),
            "adm1name": _text(row, "ADM1NAME"),
        },
    )
    global_cities = [
        city
        for feature in global_cities_raw
        if (city := _natural_earth_city_feature(feature)) is not None
    ]

    layers["countries"] = _collection(countries)
    layers["coastline"] = _collection(coastline)
    layers["borders"] = _collection(borders)
    layers["lakes"] = _collection(
        _inside_na_detail(list(layers.get("lakes", {}).get("features", []))) + _outside_na_detail(global_lakes)
    )
    layers["rivers"] = _collection(
        _inside_na_detail(list(layers.get("rivers", {}).get("features", []))) + _outside_na_detail(global_rivers)
    )
    layers["cities"] = _collection(
        _dedupe_point_features(list(layers.get("cities", {}).get("features", [])) + global_cities)
    )

    payload["source"] = (
        "Natural Earth 110m global base layers + Natural Earth/GeoNames "
        "North America detail + GeoNames cities5000 (US spatially balanced)"
    )
    payload["bbox"] = {"west": -180.0, "south": -90.0, "east": 180.0, "north": 90.0}
    payload["counts"] = {
        name: len(collection.get("features", []))
        for name, collection in layers.items()
        if isinstance(collection, dict)
    }
    payload["selection"] = {
        "method": "global_110m_base_plus_na_detail",
        "max_bytes": MAX_ATLAS_BYTES,
        "base_detail_bbox": {
            "west": NA_DETAIL_BBOX[0],
            "south": NA_DETAIL_BBOX[1],
            "east": NA_DETAIL_BBOX[2],
            "north": NA_DETAIL_BBOX[3],
        },
        "global_layers": ["countries", "coastline", "borders", "major_cities", "major_lakes", "major_rivers"],
        "na_city_selection": payload.get("selection", {}),
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the bundled offline atlas JSON.")
    parser.add_argument("--base-atlas", type=Path, default=DEFAULT_BASE_ATLAS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--source-dir", type=Path, default=None)
    parser.add_argument("--download", action="store_true", help="Download Natural Earth zips into --source-dir.")
    args = parser.parse_args()

    if args.source_dir is None:
        with TemporaryDirectory(prefix="mesh-offline-atlas-") as temp_dir:
            source_dir = Path(temp_dir)
            _download_sources(source_dir)
            payload = build_atlas(args.base_atlas, source_dir)
    else:
        source_dir = args.source_dir
        if args.download:
            _download_sources(source_dir)
        payload = build_atlas(args.base_atlas, source_dir)

    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    encoded = text.encode("utf-8")
    if len(encoded) > MAX_ATLAS_BYTES:
        raise SystemExit(f"offline atlas is {len(encoded)} bytes; limit is {MAX_ATLAS_BYTES}")
    args.output.write_text(text, encoding="utf-8")
    print(f"wrote {args.output} ({len(encoded)} bytes)")
    print("counts:", payload["counts"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
