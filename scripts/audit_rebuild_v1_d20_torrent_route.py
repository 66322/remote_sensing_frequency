#!/usr/bin/env python3
"""D20 Stage-A transfer-route preflight for official DFC2019 Track-1 data.

This is intentionally metadata/network-only:
- no raster data download
- no peer connection for file transfer
- no BitTorrent piece request/upload
- no Google Drive retry
- no GPU work

It inspects the official .torrent metadata already downloaded and probes the
official tracker endpoint at the transport/protocol level. It also reports
whether HTTP webseeds exist, because a direct HTTP route avoids peer upload.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import socket
import struct
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_TORRENT = Path(
    "/home/jovyan/zzx/datasets/rebuild_v1_d10_dfc19/"
    "official_metadata/DFC2019_track1_trainval_v1.0.0.torrent"
)
DEFAULT_RECORD = Path(
    "/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/"
    "records/rebuild_v1_d20_source_acceptance_20260928/"
    "transfer_route_preflight.json"
)
PROTOCOL_ID = 0x41727101980
TXID = 0x44503230  # ASCII-ish deterministic D20 marker


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


def txt(v):
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="replace")
    if isinstance(v, list):
        return [txt(x) for x in v]
    if isinstance(v, dict):
        return {txt(k): txt(val) for k, val in v.items()}
    return v


def now_iso():
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def flatten_announce(obj):
    out = []
    one = obj.get(b"announce")
    if one:
        out.append(txt(one))
    for tier in obj.get(b"announce-list", []):
        if isinstance(tier, list):
            for x in tier:
                s = txt(x)
                if s not in out:
                    out.append(s)
    return out


def webseeds(obj):
    out = []
    for key in (b"url-list", b"httpseeds"):
        val = obj.get(key)
        if not val:
            continue
        vals = val if isinstance(val, list) else [val]
        for x in vals:
            s = txt(x)
            if s not in out:
                out.append(s)
    return out


def resolve(host, port):
    result = {"host": host, "port": port, "ok": False, "addresses": []}
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        addrs = []
        for fam, socktype, proto, canon, sockaddr in infos:
            item = {"family": fam, "address": sockaddr[0], "port": sockaddr[1]}
            if item not in addrs:
                addrs.append(item)
        result.update(ok=bool(addrs), addresses=addrs)
    except Exception as exc:
        result.update(error_type=type(exc).__name__, error=str(exc))
    return result


def tcp_probe(host, port, timeout=6):
    r = {"host": host, "port": port, "ok": False}
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            r.update(ok=True, peer=str(s.getpeername()))
    except Exception as exc:
        r.update(error_type=type(exc).__name__, error=str(exc))
    return r


def direct_http_probe(host, port, path="/announce", timeout=6):
    """Direct socket HTTP probe: no proxy variables and no torrent announce args."""
    r = {"host": host, "port": port, "path": path, "ok": False}
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            req = (
                f"GET {path} HTTP/1.0\r\n"
                f"Host: {host}\r\n"
                "User-Agent: D20-route-preflight/1.0\r\n"
                "Connection: close\r\n\r\n"
            ).encode("ascii")
            s.sendall(req)
            data = s.recv(4096)
        first = data.splitlines()[0].decode("latin1", errors="replace") if data else ""
        r.update(
            ok=bool(data),
            response_first_line=first,
            response_sample=data[:500].decode("latin1", errors="replace"),
        )
    except Exception as exc:
        r.update(error_type=type(exc).__name__, error=str(exc))
    return r


def udp_tracker_connect(host, port, timeout=6):
    """BEP-15 connect only. Never sends announce/piece traffic."""
    r = {"host": host, "port": port, "ok": False, "announce_sent": False}
    try:
        infos = socket.getaddrinfo(host, port, family=socket.AF_INET, type=socket.SOCK_DGRAM)
        if not infos:
            raise OSError("no IPv4 UDP address")
        addr = infos[0][4]
        payload = struct.pack(">QII", PROTOCOL_ID, 0, TXID)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(timeout)
            s.sendto(payload, addr)
            data, peer = s.recvfrom(2048)
        if len(data) < 16:
            raise RuntimeError(f"short UDP tracker response: {len(data)} bytes")
        action, txid, connection_id = struct.unpack(">IIQ", data[:16])
        r.update(
            ok=(action == 0 and txid == TXID),
            peer=str(peer),
            action=action,
            transaction_id=txid,
            connection_id_hex=hex(connection_id),
        )
    except Exception as exc:
        r.update(error_type=type(exc).__name__, error=str(exc))
    return r


def command_inventory():
    names = ["aria2c", "transmission-cli", "qbittorrent-nox", "conda", "mamba", "micromamba"]
    return {name: shutil.which(name) for name in names}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--torrent", type=Path, default=DEFAULT_TORRENT)
    ap.add_argument("--out", type=Path, default=DEFAULT_RECORD)
    args = ap.parse_args()

    torrent = args.torrent.resolve()
    out = args.out.resolve()
    allowed = Path("/home/jovyan/zzx").resolve()
    for p in (torrent, out):
        if allowed != p and allowed not in p.parents:
            raise SystemExit(f"refusing path outside {allowed}: {p}")
    if not torrent.is_file():
        raise SystemExit(f"torrent not found: {torrent}")

    obj = BDecoder(torrent.read_bytes()).parse()
    trackers = flatten_announce(obj)
    seeds = webseeds(obj)

    tracker_probes = []
    for uri in trackers:
        u = urlparse(uri)
        host = u.hostname
        if not host:
            tracker_probes.append({"uri": uri, "error": "no hostname"})
            continue
        port = u.port or (443 if u.scheme == "https" else 80)
        item = {
            "uri": uri,
            "scheme": u.scheme,
            "dns": resolve(host, port),
        }
        if u.scheme in ("http", "https"):
            item["tcp"] = tcp_probe(host, port)
            if u.scheme == "http":
                item["direct_http_no_announce_args"] = direct_http_probe(
                    host, port, u.path or "/announce"
                )
        elif u.scheme == "udp":
            item["udp_connect_only"] = udp_tracker_connect(host, port)
        tracker_probes.append(item)

    any_tracker_transport = False
    for item in tracker_probes:
        if item.get("tcp", {}).get("ok"):
            any_tracker_transport = True
        if item.get("direct_http_no_announce_args", {}).get("ok"):
            any_tracker_transport = True
        if item.get("udp_connect_only", {}).get("ok"):
            any_tracker_transport = True

    if seeds:
        status = "DIRECT_WEBSEED_METADATA_PRESENT"
        next_action = (
            "Validate each official webseed URL and, if it serves the two Track-1 packages, "
            "use direct HTTP(S) download with checksum logging; do not use peer transfer."
        )
    elif any_tracker_transport:
        status = "TRACKER_REACHABLE_NO_WEBSEED"
        next_action = (
            "The torrent route is technically reachable but no direct webseed is advertised. "
            "Do not start a peer download automatically because ordinary BitTorrent may upload "
            "pieces. Prefer registered DataPort/direct-owner download or obtain an explicit "
            "download route consistent with the dataset terms."
        )
    else:
        status = "NO_SERVER_TRANSFER_ROUTE_CONFIRMED"
        next_action = (
            "No webseed and no tracker transport was confirmed. Use a registered browser/direct "
            "owner route outside the blocked server proxy, or execute the one-time Houston fallback "
            "check if US3D cannot be obtained."
        )

    result = {
        "schema_version": "1.0",
        "created_at": now_iso(),
        "stage": "D20_A_transfer_route_preflight",
        "torrent": str(torrent),
        "tracker_uris": trackers,
        "webseed_uris": seeds,
        "tracker_probes": tracker_probes,
        "commands": command_inventory(),
        "proxy_environment_present": {
            k: bool(os.environ.get(k))
            for k in (
                "http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY",
                "all_proxy", "ALL_PROXY", "no_proxy", "NO_PROXY"
            )
        },
        "data_transfer_performed": False,
        "torrent_announce_performed": False,
        "peer_piece_transfer_performed": False,
        "google_drive_retry_performed": False,
        "status": status,
        "next_action": next_action,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
