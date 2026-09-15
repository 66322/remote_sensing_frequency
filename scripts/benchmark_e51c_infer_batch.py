import gc
import json
import time
from pathlib import Path

import numpy as np
import torch

# Reuse the frozen E51-C implementation directly.
import eval_e51c_fixed_grid_information_degradation as e51c


ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
OUT = ROOT / "records" / "e51c_infer_batch_benchmark_20260915"
OUT.mkdir(parents=True, exist_ok=True)

TILE_ID = "4_10"
REGION = 2048
BATCHES = [8, 16, 32]


def center_crop(data, size):
    h, w = data["dsm"].shape
    y0 = (h - size) // 2
    x0 = (w - size) // 2
    y1 = y0 + size
    x1 = x0 + size
    return {
        "optical": data["optical"][y0:y1, x0:x1, :].copy(),
        "dsm": data["dsm"][y0:y1, x0:x1].copy(),
        "full_gt": data["full_gt"][y0:y1, x0:x1].copy(),
        "noboundary_gt": data["noboundary_gt"][y0:y1, x0:x1].copy(),
    }


def timed_predict(net, model_name, optical, dsm, batch):
    old_batch = e51c.INFER_BATCH
    try:
        e51c.INFER_BATCH = int(batch)
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        pred = e51c.infer_tile(net, model_name, optical, dsm)
        torch.cuda.synchronize()
        seconds = time.perf_counter() - t0
        peak_gib = torch.cuda.max_memory_allocated() / (1024 ** 3)
        return pred, float(seconds), float(peak_gib), None
    except torch.cuda.OutOfMemoryError as ex:
        torch.cuda.empty_cache()
        return None, None, None, f"CUDA OOM: {ex}"
    finally:
        e51c.INFER_BATCH = old_batch
        gc.collect()


def main():
    print("=" * 100)
    print("E51-C INFERENCE BATCH BENCHMARK")
    print("=" * 100)
    print("tile:", TILE_ID)
    print("center region:", REGION, "x", REGION)
    print("patch:", e51c.PATCH)
    print("stride:", e51c.TEST_STRIDE)
    print("batches:", BATCHES)
    print("NOTE: benchmark changes batch only; patch/stride/model/input stay fixed.")

    native = e51c.load_test_tile(TILE_ID)
    crop = center_crop(native, REGION)

    pp_net, _, _ = e51c.build_model("PP4k", e51c.PP_CKPT)
    ph_net, _, _ = e51c.build_model("PH4k", e51c.PH_CKPT)

    models = [
        ("PP4k", pp_net),
        ("PH4k", ph_net),
    ]

    summary = {
        "tile_id": TILE_ID,
        "region": REGION,
        "patch": e51c.PATCH,
        "stride": e51c.TEST_STRIDE,
        "batches": BATCHES,
        "models": {},
    }

    for model_name, net in models:
        print()
        print("#" * 100)
        print(model_name)
        print("#" * 100)

        reference = None
        ref_seconds = None
        rows = []

        for batch in BATCHES:
            pred, seconds, peak_gib, error = timed_predict(
                net,
                model_name,
                crop["optical"],
                crop["dsm"],
                batch,
            )

            if error is not None:
                row = {
                    "batch": batch,
                    "seconds": None,
                    "speedup_vs_batch8": None,
                    "peak_allocated_gib": None,
                    "prediction_equal_to_batch8": False,
                    "different_pixels": None,
                    "error": error,
                }
                rows.append(row)
                print(f"batch={batch:>2d} | OOM")
                continue

            if batch == 8:
                reference = pred.copy()
                ref_seconds = seconds
                equal = True
                diff_pixels = 0
            else:
                if reference is None:
                    raise RuntimeError("batch=8 reference was not produced")
                diff_pixels = int(np.count_nonzero(pred != reference))
                equal = diff_pixels == 0

            speedup = ref_seconds / seconds if ref_seconds is not None else None

            row = {
                "batch": batch,
                "seconds": seconds,
                "speedup_vs_batch8": speedup,
                "peak_allocated_gib": peak_gib,
                "prediction_equal_to_batch8": bool(equal),
                "different_pixels": diff_pixels,
                "error": None,
            }
            rows.append(row)

            print(
                f"batch={batch:>2d} | {seconds:8.3f}s | "
                f"speedup={speedup:5.2f}x | peak={peak_gib:5.2f} GiB | "
                f"same_pred={equal} | diff_pixels={diff_pixels}"
            )

        summary["models"][model_name] = rows

    safe_batches = []
    for batch in BATCHES:
        if batch == 8:
            safe_batches.append(batch)
            continue
        ok = True
        for model_name in ("PP4k", "PH4k"):
            row = next(
                r for r in summary["models"][model_name] if r["batch"] == batch
            )
            if row["error"] is not None or not row["prediction_equal_to_batch8"]:
                ok = False
                break
        if ok:
            safe_batches.append(batch)

    summary["safe_batches_exact_prediction_on_benchmark"] = safe_batches
    summary["recommended_batch"] = max(safe_batches) if safe_batches else 8
    summary["warning"] = (
        "This benchmark establishes exact final-label equality only on one 2048x2048 region. "
        "Keep patch=512 and stride=64 for formal E51-C. Before publication, retain the historical "
        "batch-8 results already produced as the reference and record the benchmark evidence when "
        "using a larger batch for additional diagnostic conditions."
    )

    out_path = OUT / "benchmark.json"
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print("=" * 100)
    print("SAFE BATCHES:", safe_batches)
    print("RECOMMENDED:", summary["recommended_batch"])
    print("OUTPUT:", out_path)
    print("=" * 100)


if __name__ == "__main__":
    main()
