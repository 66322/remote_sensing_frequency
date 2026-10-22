"""Read-only public-data preflight; one development sample per geographic group."""
import argparse
import json
from pathlib import Path

import numpy as np

from phase3_combined_plan import public_catalog_status, read
from phase3_public_data import TileCache


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--catalog",type=Path,required=True)
    parser.add_argument("--sample-headers",action="store_true")
    args=parser.parse_args()
    status=public_catalog_status(args.catalog)
    print(json.dumps(status,ensure_ascii=False,indent=2))
    if not args.sample_headers:
        return
    if not all(status[name]["ready"] for name in ("3DCD","P3")):
        raise RuntimeError("catalog incomplete; no data pixels inspected")
    catalog=read(args.catalog)
    for name in ("3DCD","P3"):
        config=catalog["datasets"][name]
        rows=config["development"]
        cache=TileCache(name,config["metadata"],max_bytes=1024**3)
        for group in sorted({row["group"] for row in rows}):
            row=next(row for row in rows if row["group"]==group)
            item=cache.get(row)
            if name=="3DCD":
                report=dict(dataset=name,group=group,id=row["id"],
                            shape=list(item["valid"].shape),valid_pixels=int(item["valid"].sum()),
                            changed_pixels=int(item["changed"].sum()),
                            finite_height=bool(np.isfinite(item["delta"]).all()))
            else:
                report=dict(dataset=name,group=group,id=row["id"],
                            shape=list(item["instance"].shape),
                            LiDAR_covered_pixels=int(item["height_valid"].sum()),
                            building_instances=int(item["instance"].max()))
            print(json.dumps(report,ensure_ascii=False))
        cache.clear()


if __name__=="__main__":main()
