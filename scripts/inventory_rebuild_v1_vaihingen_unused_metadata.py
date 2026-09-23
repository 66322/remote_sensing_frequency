"""Inventory Vaihingen filenames and ZIP member names, never image pixels.

Only the two legacy Vaihingen roots are examined. Potsdam and Test6 are not
traversed. A possible unused ID is not yet a frozen or independent test scene.
"""

import re
import zipfile
from collections import defaultdict
from pathlib import Path

ROOTS = (
    Path("/home/jovyan/zzx/projects_zys/raw_extract/Vaihingen"),
    Path("/home/jovyan/zzx/projects_zys/ISPRS_dataset/Vaihingen"),
)
USED_TRAIN = {1, 3, 7, 11, 13, 17, 23, 26, 28, 32, 34, 37}
USED_EVAL = {5, 15, 21, 30}
AREA = re.compile(r"area(\d+)", re.IGNORECASE)


def category(name):
    p = name.replace("\\", "/").lower()
    if not p.endswith((".tif", ".tiff")):
        return None
    if "gts" in p or "ground_truth" in p or "label" in p:
        if "complete" in p:
            return "label_complete"
        if "participant" in p:
            return "label_participant"
        return "label_other"
    if "/dsm/" in p or Path(p).name.startswith("dsm_"):
        return "dsm"
    if "/top/" in p or Path(p).name.startswith("top_mosaic_"):
        return "optical"
    return None


def inventory():
    seen = defaultdict(set)
    counts = defaultdict(int)
    for root in ROOTS:
        print(f"ROOT {root} exists={root.is_dir()}")
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() == ".zip":
                counts["zip_archives"] += 1
                try:
                    with zipfile.ZipFile(path) as archive:
                        names = archive.namelist()
                except (OSError, zipfile.BadZipFile) as exc:
                    print(f"ZIP_UNREADABLE {path.name} {type(exc).__name__}")
                    continue
                for member in names:
                    counts["zip_members_examined"] += 1
                    match = AREA.search(member)
                    kind = category(member)
                    if match and kind:
                        seen[kind].add(int(match.group(1)))
                continue
            counts["files_examined"] += 1
            match = AREA.search(path.name)
            kind = category(str(path))
            if match and kind:
                seen[kind].add(int(match.group(1)))
    return seen, counts


def main():
    seen, counts = inventory()
    print("METADATA_ONLY", dict(counts))
    for kind in ("optical", "dsm", "label_participant", "label_complete", "label_other"):
        ids = sorted(seen[kind])
        print(f"{kind} count={len(ids)} ids={','.join(map(str, ids)) or 'NONE'}")
    complete = seen["optical"] & seen["dsm"] & seen["label_complete"]
    possible = complete - USED_TRAIN - USED_EVAL
    print("LEGACY_USED_TRAIN", ",".join(map(str, sorted(USED_TRAIN))))
    print("LEGACY_USED_EVAL", ",".join(map(str, sorted(USED_EVAL))))
    print("POSSIBLE_UNUSED_COMPLETE_TRIPLETS", ",".join(map(str, sorted(possible))) or "NONE")
    print("No TIFF pixels or label arrays were opened; ZIP central directories only.")
    print("Possible unused IDs require prior-exposure and spatial-neighbor checks before any split is frozen.")


if __name__ == "__main__":
    main()
