"""Decode one large light-evidence JSON; verify original size/SHA before writing.

Small plain JSON is copied unchanged. Existing files are never overwritten.
"""
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path

RECORD_ENCODING = 'gzip-base64-exact-v1'

def encode_record(raw):
    """Preserve original bytes exactly; keep small JSON directly readable."""
    if len(raw) < 1024 * 1024:
        return raw
    packed = gzip.compress(raw, compresslevel=6, mtime=0)
    envelope = dict(record_encoding=RECORD_ENCODING,
                    original_bytes=len(raw),
                    original_sha256=hashlib.sha256(raw).hexdigest(),
                    payload_base64=base64.b64encode(packed).decode('ascii'))
    encoded = (json.dumps(envelope, separators=(',', ':')) + '\n').encode()
    if len(encoded) >= len(raw):
        return raw
    if decode_record(encoded) != raw:
        raise ValueError('lossless record round-trip failed')
    return encoded

def decode_record(raw):
    value = json.loads(raw)
    if not isinstance(value, dict) or value.get('record_encoding') != RECORD_ENCODING:
        return raw
    decoded = gzip.decompress(base64.b64decode(value['payload_base64'], validate=True))
    if len(decoded) != value['original_bytes']:
        raise ValueError('decoded size mismatch')
    if hashlib.sha256(decoded).hexdigest() != value['original_sha256']:
        raise ValueError('decoded SHA256 mismatch')
    return decoded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    decoded = decode_record(args.input.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('xb') as handle:
        handle.write(decoded)
    print('DECODED_BYTES=%d SHA256=%s' % (len(decoded), hashlib.sha256(decoded).hexdigest()))

if __name__ == '__main__':
    main()
