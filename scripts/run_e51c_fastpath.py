import argparse
import json
from pathlib import Path

import numpy as np
import torch

import eval_e51c_fixed_grid_information_degradation as e51c


ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
BENCHMARK_JSON = (
    ROOT
    / "records"
    / "e51c_fastpath_benchmark_20260915"
    / "benchmark.json"
)
REQUIRED_PATH = "gpu_input_gpu_score"
REQUIRED_BATCH = 8
REQUIRED_DTYPE = "float32"


def verify_benchmark_gate():
    if not BENCHMARK_JSON.is_file():
        raise FileNotFoundError(
            "Fast-path benchmark result is missing. Run "
            "scripts/benchmark_e51c_fastpath.py first: "
            f"{BENCHMARK_JSON}"
        )

    data = json.loads(BENCHMARK_JSON.read_text(encoding="utf-8"))

    if int(data.get("patch", -1)) != int(e51c.PATCH):
        raise RuntimeError("Benchmark patch size does not match current E51-C protocol")
    if int(data.get("stride", -1)) != int(e51c.TEST_STRIDE):
        raise RuntimeError("Benchmark stride does not match current E51-C protocol")
    if int(data.get("batch", -1)) != REQUIRED_BATCH:
        raise RuntimeError("Benchmark batch does not match required historical batch=8")
    if str(data.get("dtype")) != REQUIRED_DTYPE:
        raise RuntimeError("Benchmark dtype does not match required FP32 protocol")

    safe_paths = set(data.get("exact_prediction_safe_paths_on_benchmark", []))
    if REQUIRED_PATH not in safe_paths:
        raise RuntimeError(
            f"Required path {REQUIRED_PATH!r} did not pass the exact-prediction benchmark"
        )

    for model_name in ("PP4k", "PH4k"):
        rows = data.get("models", {}).get(model_name, [])
        row = next((r for r in rows if r.get("path") == REQUIRED_PATH), None)
        if row is None:
            raise RuntimeError(f"Benchmark row missing for {model_name}/{REQUIRED_PATH}")
        if not bool(row.get("prediction_equal_to_reference")):
            raise RuntimeError(f"Exact-prediction gate failed for {model_name}/{REQUIRED_PATH}")
        if int(row.get("different_pixels", -1)) != 0:
            raise RuntimeError(f"Non-zero prediction difference for {model_name}/{REQUIRED_PATH}")

    return data


def prepare_gpu_tiles(optical, dsm):
    optical_chw = np.ascontiguousarray(optical.transpose(2, 0, 1))
    dsm_hw = np.ascontiguousarray(dsm)

    optical_gpu = torch.from_numpy(optical_chw).to(
        e51c.DEVICE,
        non_blocking=False,
    )
    dsm_gpu = torch.from_numpy(dsm_hw).to(
        e51c.DEVICE,
        non_blocking=False,
    )
    return optical_gpu, dsm_gpu


def infer_gpu_input_gpu_score(net, model_name, optical, dsm):
    """
    Exact-gated diagnostic fast path.

    Frozen protocol items are unchanged:
      - patch = 512
      - stride = 64
      - inference batch = 8
      - FP32
      - coordinate order
      - checkpoint/model/input
      - PH scale = 1.0 on the native Potsdam grid

    Only data placement changes: the full tile and score accumulator stay on GPU.
    """
    if int(e51c.INFER_BATCH) != REQUIRED_BATCH:
        raise RuntimeError(
            f"Fast path requires historical INFER_BATCH={REQUIRED_BATCH}, "
            f"got {e51c.INFER_BATCH}"
        )

    h, w = dsm.shape
    ys = e51c.make_positions(h)
    xs = e51c.make_positions(w)
    coords = [(y, x) for y in ys for x in xs]

    optical_gpu, dsm_gpu = prepare_gpu_tiles(optical, dsm)
    score = torch.zeros(
        (e51c.N_CLASSES, h, w),
        dtype=torch.float32,
        device=e51c.DEVICE,
    )

    with torch.inference_mode():
        for start in range(0, len(coords), REQUIRED_BATCH):
            batch_coords = coords[start : start + REQUIRED_BATCH]

            op = torch.stack(
                [
                    optical_gpu[
                        :,
                        y : y + e51c.PATCH,
                        x : x + e51c.PATCH,
                    ]
                    for y, x in batch_coords
                ],
                dim=0,
            ).contiguous()

            ds = torch.stack(
                [
                    dsm_gpu[
                        y : y + e51c.PATCH,
                        x : x + e51c.PATCH,
                    ]
                    for y, x in batch_coords
                ],
                dim=0,
            ).contiguous()

            if model_name == "PH4k":
                net.set_sample_scales([1.0] * len(batch_coords))

            logits = net(op, ds)

            # Preserve the historical patch accumulation order.
            for output, (y, x) in zip(logits, batch_coords):
                score[
                    :,
                    y : y + e51c.PATCH,
                    x : x + e51c.PATCH,
                ].add_(output)

            del op, ds, logits

    pred = torch.argmax(score, dim=0).to(torch.uint8).cpu().numpy()
    del optical_gpu, dsm_gpu, score
    return pred


def resolve_out_dir():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--out", type=Path, default=e51c.DEFAULT_OUT)
    known, _ = parser.parse_known_args()
    return known.out


def annotate_metadata(out_dir, benchmark):
    metadata_path = out_dir / "metadata.json"
    if not metadata_path.is_file():
        return

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["inference_implementation"] = REQUIRED_PATH
    metadata["fastpath_benchmark_json"] = str(BENCHMARK_JSON)
    metadata["fastpath_gate"] = {
        "patch": int(benchmark["patch"]),
        "stride": int(benchmark["stride"]),
        "batch": int(benchmark["batch"]),
        "dtype": str(benchmark["dtype"]),
        "benchmark_region": int(benchmark["region"]),
        "benchmark_tile": str(benchmark["tile_id"]),
        "exact_prediction_safe_on_benchmark": True,
        "different_pixels_PP4k": 0,
        "different_pixels_PH4k": 0,
    }
    metadata["fastpath_scope_warning"] = (
        "Exact equality was established on the recorded 2048x2048 benchmark region. "
        "Historical batch-8/stride-64 outputs remain the frozen formal reference; "
        "this fast path is used for additional diagnostic conditions."
    )
    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main():
    benchmark = verify_benchmark_gate()
    out_dir = resolve_out_dir()

    print("=" * 100)
    print("E51-C EXACT-GATED GPU FAST PATH")
    print("=" * 100)
    print("implementation:", REQUIRED_PATH)
    print("patch:", e51c.PATCH)
    print("stride:", e51c.TEST_STRIDE)
    print("batch:", e51c.INFER_BATCH)
    print("dtype: FP32")
    print("benchmark gate: PASS (0 final-label diff on PP4k and PH4k benchmark region)")
    print("NOTE: historical reference results remain unchanged; this runner is for new diagnostics.")
    print("=" * 100)

    e51c.infer_tile = infer_gpu_input_gpu_score
    e51c.main()
    annotate_metadata(out_dir, benchmark)


if __name__ == "__main__":
    main()
