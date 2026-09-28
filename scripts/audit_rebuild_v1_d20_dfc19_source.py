#!/usr/bin/env python3
"""D20 Stage-A source audit for US3D/DFC19.

This script performs a bounded, CPU-only acceptance probe. It deliberately
does NOT retry the previously blocked Google Drive route and does NOT start
model training. Network traffic is limited to small official/public metadata
pages and the official JHU/APL Track-1 torrent metadata file.

Outputs are written below /home/jovyan/zzx by default.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

DEFAULT_DATA_ROOT = Path("/home/jovyan/zzx/datasets/rebuild_v1_d10_dfc19")
DEFAULT_RECORD_DIR = Path(
    "/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/"
    "records/rebuild_v1_d20_source_acceptance_20260928"
)

GRSS_URL = (
    "https://www.grss-ieee.org/community/technical-committees/"
    "2019-ieee-grss-data-fusion-contest/"
)
DATAPORT_URL = "https://ieee-dataport.org/open-access/data-fusion-contest-2019-dfc2019"
TORRENT_URL = (
    "https://raw.githubusercontent.com/pubgeo/dfc2019/master/data/"
    "DFC2019_track1_trainval_v1.0.0.torrent"
)
TORRENT_NAME = "DFC2019_track1_trainval_v1.0.0.torrent"

SUFFIX_RE = re.compile(r"^(?P<prefix>.+)_(?P<role>RGB|AGL|CLS)\.tiff?$", re.I)
CITY_TILE_RE = re.compile(r"^(?P<city>JAX|OMA)_(?P<tile>\d+)(?:_|$)", re.I)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def probe_url(url: str, timeout: int = 20) -> dict:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 D20-source-audit/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            sample = r.read(1024)
            return {
                "url": url,
                "ok": True,
                "status": getattr(r, "status", None),
                "content_type": r.headers.get("Content-Type"),
                "content_length": r.headers.get("Content-Length"),
                "sample_bytes": len(sample),
                "final_url": r.geturl(),
            }
    except Exception as exc:
        return {
            "url": url,
            "ok": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def download_small_file(url: str, out: Path, timeout: int = 60) -> dict:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".part")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 D20-source-audit/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r, tmp.open("wb") as f:
            total = 0
            while True:
                chunk = r.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > 2 * 1024 * 1024:
                    raise RuntimeError("refusing metadata download larger than 2 MiB")
                f.write(chunk)
        tmp.replace(out)
        return {
            "ok": True,
            "path": str(out),
            "size_bytes": out.stat().st_size,
            "sha256": sha256(out),
        }
    except Exception as exc:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        return {
            "ok": False,
            "path": str(out),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


class BDecoder:
    def __init__(self, data: bytes):
        self.data = data
        self.i = 0

    def parse(self):
        c = self.data[self.i:self.i + 1]
        if c == b"i":
            self.i += 1
            j = self.data.index(b"e", self.i)
            n = int(self.data[self.i:j])
            self.i = j + 1
            return n
        if c == b"l":
            self.i += 1
            out = []
            while self.data[self.i:self.i + 1] != b"e":
                out.append(self.parse())
            self.i += 1
            return out
        if c == b"d":
            self.i += 1
            out = {}
            while self.data[self.i:self.i + 1] != b"e":
                k = self.parse()
                v = self.parse()
                out[k] = v
            self.i += 1
            return out
        if c.isdigit():
            j = self.data.index(b":", self.i)
            n = int(self.data[self.i:j])
            self.i = j + 1
            out = self.data[self.i:self.i + n]
            self.i += n
            return out
        raise ValueError(f"invalid bencode at offset {self.i}")


def bstr(x) -> str:
    if isinstance(x, bytes):
        return x.decode("utf-8", errors="replace")
    return str(x)


def inspect_torrent(path: Path) -> dict:
    raw = path.read_bytes()
    obj = BDecoder(raw).parse()
    info = obj.get(b"info", {})
    files = []
    if b"files" in info:
        for item in info[b"files"]:
            parts = [bstr(x) for x in item.get(b"path", [])]
            files.append(
                {"path": "/".join(parts), "length_bytes": int(item.get(b"length", 0))}
            )
    else:
        files.append(
            {
                "path": bstr(info.get(b"name", b"")),
                "length_bytes": int(info.get(b"length", 0)),
            }
        )
    announces = []
    if b"announce" in obj:
        announces.append(bstr(obj[b"announce"]))
    for tier in obj.get(b"announce-list", []):
        for item in tier:
            s = bstr(item)
            if s not in announces:
                announces.append(s)
    total = sum(x["length_bytes"] for x in files)
    wanted = [
        x for x in files
        if ("Train-Track1-RGB" in x["path"] or "Train-Track1-Truth" in x["path"])
    ]
    return {
        "name": bstr(info.get(b"name", b"")),
        "file_count": len(files),
        "total_size_bytes": total,
        "announce_urls": announces,
        "wanted_files": wanted,
        "all_files": files,
    }


def inventory_local(data_root: Path) -> dict:
    roles = defaultdict(dict)
    city_tiles = defaultdict(set)
    tif_count = 0
    for p in data_root.rglob("*") if data_root.exists() else []:
        if not p.is_file() or p.suffix.lower() not in {".tif", ".tiff"}:
            continue
        tif_count += 1
        m = SUFFIX_RE.match(p.name)
        if not m:
            continue
        prefix = m.group("prefix")
        role = m.group("role").upper()
        roles[prefix][role] = str(p)
        cm = CITY_TILE_RE.match(prefix)
        if cm:
            city_tiles[cm.group("city").upper()].add(cm.group("tile"))
    triplets = []
    for prefix, mapping in sorted(roles.items()):
        if {"RGB", "AGL", "CLS"} <= set(mapping):
            triplets.append(
                {
                    "prefix": prefix,
                    "rgb": mapping["RGB"],
                    "agl": mapping["AGL"],
                    "cls": mapping["CLS"],
                }
            )
    return {
        "data_root": str(data_root),
        "exists": data_root.exists(),
        "tif_count": tif_count,
        "matched_triplet_count": len(triplets),
        "triplet_examples": triplets[:20],
        "city_tile_counts": {k: len(v) for k, v in sorted(city_tiles.items())},
    }


def command_versions() -> dict:
    out = {}
    for cmd in ("curl", "wget", "aria2c", "transmission-cli", "git"):
        exe = shutil.which(cmd)
        if not exe:
            out[cmd] = {"available": False}
            continue
        try:
            cp = subprocess.run(
                [exe, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=5,
                check=False,
            )
            first = cp.stdout.splitlines()[0] if cp.stdout else ""
        except Exception as exc:
            first = f"{type(exc).__name__}: {exc}"
        out[cmd] = {"available": True, "path": exe, "version": first}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    ap.add_argument("--record-dir", type=Path, default=DEFAULT_RECORD_DIR)
    args = ap.parse_args()

    data_root = args.data_root.resolve()
    record_dir = args.record_dir.resolve()
    allowed = Path("/home/jovyan/zzx").resolve()
    for p in (data_root, record_dir):
        if allowed != p and allowed not in p.parents:
            raise SystemExit(f"refusing path outside {allowed}: {p}")

    record_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir = data_root / "official_metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    torrent_path = metadata_dir / TORRENT_NAME

    disk = shutil.disk_usage(allowed)
    local = inventory_local(data_root)
    probes = {
        "grss": probe_url(GRSS_URL),
        "dataport": probe_url(DATAPORT_URL),
        "github_torrent": probe_url(TORRENT_URL),
    }

    torrent_download = (
        {"ok": True, "path": str(torrent_path), "existing": True,
         "size_bytes": torrent_path.stat().st_size, "sha256": sha256(torrent_path)}
        if torrent_path.is_file()
        else download_small_file(TORRENT_URL, torrent_path)
    )
    torrent = None
    torrent_error = None
    if torrent_download.get("ok"):
        try:
            torrent = inspect_torrent(torrent_path)
        except Exception as exc:
            torrent_error = f"{type(exc).__name__}: {exc}"

    if local["matched_triplet_count"] > 0:
        status = "LOCAL_TRIPLETS_PRESENT_CONTENT_VALIDATION_PENDING"
        decision = (
            "Potentially usable local Track-1 triplets exist. Next inspect raster metadata, "
            "class codes, geographic split and publication-use approval before training."
        )
    elif torrent_download.get("ok"):
        status = "BLOCKED_DATA_TRANSFER_AND_TERMS_PENDING"
        decision = (
            "Official JHU/APL torrent metadata is reachable, so the old Google Drive 403 is "
            "not the only route. However no local RGB/AGL/CLS triplets were confirmed; do not "
            "start D20 training until data transfer and publication-use conditions are resolved."
        )
    else:
        status = "BLOCKED_NO_WORKING_SERVER_ACCESS_ROUTE"
        decision = (
            "No local triplets and no reachable official torrent metadata were confirmed. "
            "After this bounded probe, assess the Houston fallback once rather than retrying "
            "the unchanged Google Drive route."
        )

    result = {
        "schema_version": "1.0",
        "stage": "D20_A_source_acceptance",
        "created_at": now_iso(),
        "status": status,
        "decision": decision,
        "google_drive_retry_performed": False,
        "test6_loaded": False,
        "gpu_used": False,
        "official_facts_frozen": {
            "candidate": "US3D / DFC2019 Track 1",
            "required_modalities": ["RGB", "AGL", "CLS"],
            "classes_las": {
                "2": "Ground",
                "5": "Trees",
                "6": "Buildings",
                "9": "Water",
                "17": "Bridge / elevated road",
                "65": "Unlabeled",
            },
            "car_class_available": False,
            "height_unit": "meters above ground level",
            "track1_image_size": "1024x1024",
            "final_claim_limit": "Cannot validate Potsdam Car/small-car behavior on DFC19.",
        },
        "paths": {
            "data_root": str(data_root),
            "record_dir": str(record_dir),
            "torrent_path": str(torrent_path),
        },
        "disk": {
            "free_bytes": disk.free,
            "free_gib": round(disk.free / 1024**3, 2),
        },
        "commands": command_versions(),
        "network_probes": probes,
        "torrent_download": torrent_download,
        "torrent_parse_error": torrent_error,
        "torrent": torrent,
        "local_inventory": local,
        "next_action": (
            "If status shows local triplets, run the D20 raster/header and geographic split audit. "
            "If only torrent metadata is reachable, confirm dataset terms and transfer only Track-1 "
            "RGB + Truth packages. If both official routes remain blocked, evaluate Houston once."
        ),
    }

    (record_dir / "source_audit.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if torrent:
        with (record_dir / "torrent_files.tsv").open("w", encoding="utf-8") as f:
            f.write("length_bytes\tpath\n")
            for item in torrent["all_files"]:
                f.write(f'{item["length_bytes"]}\t{item["path"]}\n')
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
