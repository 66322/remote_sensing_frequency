"""Check Vaihingen D10 source readiness without reading image or label pixels.

Only the two known Vaihingen roots are traversed. GeoTIFF headers are read
with rasterio if available; ZIP central directories are listed, never opened
as rasters. This script never visits Potsdam or historical Test6.
"""

import json
import zipfile
from collections import defaultdict
from pathlib import Path

from inventory_rebuild_v1_vaihingen_unused_metadata import (
    AREA,
    ROOTS,
    USED_EVAL,
    USED_TRAIN,
    category,
)

try:
    import rasterio
except ImportError:
    rasterio = None
try:
    import tifffile
except ImportError:
    tifffile = None


def collect():
    sources = defaultdict(lambda: defaultdict(list))
    for root in ROOTS:
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() == ".zip":
                try:
                    with zipfile.ZipFile(path) as archive:
                        for member in archive.namelist():
                            match, kind = AREA.search(member), category(member)
                            if match and kind:
                                sources[int(match.group(1))][kind].append(
                                    {"where": "zip", "path": str(path), "member": member}
                                )
                except (OSError, zipfile.BadZipFile) as exc:
                    print("ZIP_UNREADABLE", path, type(exc).__name__)
                continue
            match, kind = AREA.search(path.name), category(str(path))
            if match and kind:
                sources[int(match.group(1))][kind].append(
                    {"where": "disk", "path": str(path)}
                )
    return sources


def header(path):
    if rasterio is None:
        return tiff_header(path)
    try:
        with rasterio.open(path) as ds:
            return {
                "shape": [ds.height, ds.width],
                "bands": ds.count,
                "crs": str(ds.crs) if ds.crs else None,
                "bounds": [round(v, 3) for v in ds.bounds],
                "pixel_size": [round(abs(ds.transform.a), 5), round(abs(ds.transform.e), 5)],
                "georeferenced": bool(ds.crs and not ds.transform.is_identity),
            }
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def tiff_header(path):
    """Fallback for conventional north-up GeoTIFFs; no page.asarray call."""
    if tifffile is None:
        return {"error": "rasterio and tifffile unavailable"}
    try:
        with tifffile.TiffFile(path) as tf:
            page = tf.pages[0]
            tags = page.tags
            shape = [page.imagelength, page.imagewidth]
            result = {
                "shape": shape,
                "bands": page.samplesperpixel,
                "crs": None,
                "bounds": None,
                "pixel_size": None,
                "georeferenced": False,
            }
            scale_tag, tie_tag = tags.get(33550), tags.get(33922)
            keys_tag = tags.get(34735)
            if keys_tag:
                keys = keys_tag.value
                for offset in range(4, len(keys), 4):
                    key_id, location, count, value = keys[offset:offset + 4]
                    if key_id in (3072, 2048) and location == 0 and count == 1:
                        result["crs"] = f"EPSG:{value}"
                        break
            if scale_tag and tie_tag:
                sx, sy = map(float, scale_tag.value[:2])
                pixel_i, pixel_j, _, world_x, world_y, _ = map(float, tie_tag.value[:6])
                left, top = world_x - pixel_i * sx, world_y + pixel_j * sy
                result["bounds"] = [round(left, 3), round(top - shape[0] * sy, 3),
                                    round(left + shape[1] * sx, 3), round(top, 3)]
                result["pixel_size"] = [round(abs(sx), 5), round(abs(sy), 5)]
                result["georeferenced"] = bool(result["crs"] and sx > 0 and sy > 0)
            return result
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def first_disk(entries):
    paths = sorted(e["path"] for e in entries if e["where"] == "disk")
    return paths[0] if paths else None


def gap(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    dx = max(bx0 - ax1, ax0 - bx1, 0)
    dy = max(by0 - ay1, ay0 - by1, 0)
    return round((dx * dx + dy * dy) ** 0.5, 2)


def aligned(headers):
    if any(not h or "error" in h for h in headers):
        return None
    optical, *others = headers
    if not optical["georeferenced"]:
        return None
    tolerance = max(optical["pixel_size"]) * 0.1
    return all(
        h["shape"] == optical["shape"]
        and h["crs"] == optical["crs"]
        and h["bounds"] is not None
        and all(abs(x - y) <= tolerance for x, y in zip(h["bounds"], optical["bounds"]))
        for h in others
    )


def main():
    sources = collect()
    used = USED_TRAIN | USED_EVAL
    candidates = sorted(
        i for i, kinds in sources.items()
        if i not in used and all(kinds.get(k) for k in ("optical", "dsm", "label_complete"))
    )
    print("METADATA_ONLY rasterio_available=", rasterio is not None,
          "tifffile_available=", tifffile is not None)
    print("CANDIDATE_IDS", ",".join(map(str, candidates)) or "NONE")
    print("NOTE ZIP members are not extracted files; a three-way name match is not a validated triplet.")
    optical_headers = {}
    for i in sorted(set(candidates) | used):
        optical = first_disk(sources[i].get("optical", []))
        if optical:
            optical_headers[i] = header(optical)
    for i in candidates:
        kinds = sources[i]
        row = {"id": i, "roles": {}}
        for kind in ("optical", "dsm", "label_complete"):
            entries = kinds.get(kind, [])
            disk = first_disk(entries)
            row["roles"][kind] = {
                "disk_count": sum(e["where"] == "disk" for e in entries),
                "zip_count": sum(e["where"] == "zip" for e in entries),
                "chosen_disk_path": disk,
                "first_zip_path": next((e["path"] for e in entries if e["where"] == "zip"), None),
                "header": header(disk) if disk else None,
            }
        row["extracted_triplet"] = all(
            row["roles"][k]["chosen_disk_path"] for k in row["roles"]
        )
        row["headers_aligned"] = aligned([
            row["roles"][k]["header"]
            for k in ("optical", "dsm", "label_complete")
        ])
        oh = row["roles"]["optical"]["header"]
        if oh and oh.get("georeferenced"):
            neighbors = sorted(
                (gap(oh["bounds"], other["bounds"]), j)
                for j, other in optical_headers.items()
                if j in used and other.get("georeferenced") and other.get("crs") == oh["crs"]
            )
            row["nearest_legacy_used"] = {"id": neighbors[0][1], "gap_map_units": neighbors[0][0]} if neighbors else None
        else:
            row["nearest_legacy_used"] = None
        print("CANDIDATE", json.dumps(row, ensure_ascii=False, sort_keys=True))
    print("STOP: no scene split is frozen; inspect paired headers, actual labels, prior exposure and geographic grouping first.")
    print("No raster pixels or label arrays read; Potsdam Test6 not traversed.")


if __name__ == "__main__":
    main()
