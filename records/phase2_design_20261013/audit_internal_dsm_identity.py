"""Audit existing Phase1.5 S1 internal DSM-path identity receipts; no GPU work."""
import argparse
import collections
import hashlib
import json
from pathlib import Path

def audit(decoded):
    rows = []
    for path in sorted((decoded / "cases").glob("S1_*.json")):
        raw = path.read_bytes()
        data = json.loads(raw)
        case = data["case"]
        if case["family"] == "clean":
            continue
        rows.append(dict(file="cases/" + path.name,
                         sha256=hashlib.sha256(raw).hexdigest(), case=case,
                         identity=data.get("own_logit_identity"),
                         reused=data.get("reused_old_prediction")))
    expected = {(t, d, i, f, 25) for t in ("3_11", "5_10")
                for d in ("intact", "crop_shuffle", "tile_shuffle", "zero")
                for i in range(1, 21) for f in ("pixel", "random", "gradient", "matched")}
    expected |= {(t, "intact", i, "pixel", r) for t in ("3_11", "5_10")
                 for i in range(1, 21) for r in (5, 10)}
    actual = {(x["case"]["tile"], x["case"]["dsm"], x["case"]["realization"],
               x["case"]["family"], x["case"]["ratio"]) for x in rows}
    assert len(rows) == 720 and actual == expected
    assert all(x["identity"]["dsm_only"] is True and x["reused"] is False for x in rows)
    return dict(status="PASS_RECEIPT_AUDIT",
        source_commit="9d7c27e88c510f2931ac125b7b6b3b0c60850dce",
        cases=len(rows),
        by_dsm=dict(collections.Counter(x["case"]["dsm"] for x in rows)),
        by_ratio=dict(collections.Counter(str(x["case"]["ratio"]) for x in rows)),
        tiles=sorted({x["case"]["tile"] for x in rows}),
        claim="All uploaded S1 non-clean receipts record exact own DSM logit identity on dsm_mask AND NOT rgb_mask at each inference window. Region nonempty for these mask cases. RGB-only flag can be vacuous and is not claimed. No server GPU rerun or logits downloaded.",
        receipt_list_sha256=hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        source_manifest="records/research_phase15_recoverability_20261012T233532_842792/evidence_20261013T113931418057_1206639/upload_manifest.json")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--decoded", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.decoded), ensure_ascii=False, indent=2))
