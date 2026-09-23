"""Find candidate image/height/label directories by name only; read no data.

This is a one-shot source locator, not a dataset approval or an experiment.
It does not list tiles, inspect image headers, open labels, or touch Test6.
"""

import os
from pathlib import Path

ROOT = Path("/home/jovyan/zzx").resolve()
MAX_DEPTH = 10
SKIP = {".git", ".cache", "__pycache__", "runs", "records",
        "checkpoints", "weights", "pretrain", "pretrained", "node_modules"}
GROUPS = {
    "image": {"opt", "optical", "rgb", "images", "image"},
    "height": {"gt_ndsm", "ndsm", "dsm", "height", "elevation"},
    "label": {"gt_ss_mask", "semantic", "semantics", "labels", "label", "masks", "mask"},
}


def candidate_children(names):
    lowered = {name.lower(): name for name in names}
    found = {}
    for group, aliases in GROUPS.items():
        matches = sorted((lowered[name] for name in aliases if name in lowered), key=str.lower)
        if not matches:
            return None
        found[group] = matches[0]
    return found


def main():
    if not ROOT.is_dir():
        raise RuntimeError(f"expected server root missing: {ROOT}")
    count = 0
    hits = []
    for base, dirs, _ in os.walk(ROOT, topdown=True, followlinks=False):
        path = Path(base)
        depth = len(path.relative_to(ROOT).parts)
        count += 1
        match = candidate_children(dirs)
        if match:
            hits.append((path, match))
        dirs[:] = [name for name in dirs
                   if name.lower() not in SKIP and depth < MAX_DEPTH
                   and not (path / name).is_symlink()]
    print(f"METADATA_ONLY root={ROOT} scanned_directories={count} candidates={len(hits)}")
    for path, match in sorted(hits):
        print(f"CANDIDATE root={path} image={match['image']} height={match['height']} label={match['label']}")
    print("No image, height, label, archive contents or historical Test6 tiles were opened.")
    print("Directory-name matches are not proof of labels, alignment, access rights or independent scenes.")


if __name__ == "__main__":
    main()
