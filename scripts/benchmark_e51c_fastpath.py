import gc
import json
import time
from pathlib import Path

import numpy as np
import torch

import eval_e51c_fixed_grid_information_degradation as e51c


ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
OUT = ROOT / "records" / "e51c_fastpath_benchmark_20260915"
OUT.mkdir(parents=True, exist_ok=True)

TILE_ID = "4_10"
REGION = 2048
BATCH = 8


def center_crop(data, size):
    h, w = data["dsm"].shape
    y0 = (h - size) // 2
    x0 = (w - size) // 2
    y1 = y0 + size
    x1 = x0 + size
    return {
        "optical": data["optical"][y0:y1, x0:x1, :].copy(),
        "dsm": data["dsm"][y0:y1, x0:x1].copy(),
    }


def reset_measurement():
    gc.collect()
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.synchronize()


def finish_measurement(t0):
    torch.cuda.synchronize()
    seconds = time.perf_counter() - t0
    peak_gib = torch.cuda.max_memory_allocated() / (1024 ** 3)
    return float(seconds), float(peak_gib)


def infer_reference(net, model_name, optical, dsm):
    old_batch = e51c.INFER_BATCH
    try:
        e51c.INFER_BATCH = BATCH
        return e51c.infer_tile(net, model_name, optical, dsm)
    finally:
        e51c.INFER_BATCH = old_batch


def prepare_gpu_tiles(optical, dsm):
    optical_chw = np.ascontiguousarray(optical.transpose(2, 0, 1))
    dsm_hw = np.ascontiguousarray(dsm)

    optical_gpu = torch.from_numpy(optical_chw).to(
        e51c.DEVICE, non_blocking=False
    )
    dsm_gpu = torch.from_numpy(dsm_hw).to(
        e51c.DEVICE, non_blocking=False
    )
    return optical_gpu, dsm_gpu


def coords_for_shape(h, w):
    ys = e51c.make_positions(h)
    xs = e51c.make_positions(w)
    return [(y, x) for y in ys for x in xs]


def infer_gpu_input_cpu_score(net, model_name, optical, dsm):
    """
    Keep the full Optical/DSM tile on GPU once, but preserve the historical
    CPU NumPy score accumulation order exactly.

    This removes repeated host->device patch transfers while intentionally
    leaving the output accumulation implementation unchanged.
    """
    h, w = dsm.shape
    coords = coords_for_shape(h, w)

    optical_gpu, dsm_gpu = prepare_gpu_tiles(optical, dsm)
    score = np.zeros((e51c.N_CLASSES, h, w), dtype=np.float32)

    with torch.inference_mode():
        for start in range(0, len(coords), BATCH):
            batch_coords = coords[start : start + BATCH]

            op = torch.stack(
                [
                    optical_gpu[:, y : y + e51c.PATCH, x : x + e51c.PATCH]
                    for y, x in batch_coords
                ],
                dim=0,
            ).contiguous()

            ds = torch.stack(
                [
                    dsm_gpu[y : y + e51c.PATCH, x : x + e51c.PATCH]
                    for y, x in batch_coords
                ],
                dim=0,
            ).contiguous()

            if model_name == "PH4k":
                net.set_sample_scales([1.0] * len(batch_coords))

            logits = net(op, ds).detach().cpu().numpy()

            # Deliberately identical patch-by-patch CPU accumulation order.
            for output, (y, x) in zip(logits, batch_coords):
                score[:, y : y + e51c.PATCH, x : x + e51c.PATCH] += output

            del op, ds, logits

    return np.argmax(score, axis=0).astype(np.uint8)


def infer_gpu_input_gpu_score(net, model_name, optical, dsm):
    """
    Keep inputs and score accumulation on GPU. This is potentially faster,
    but is accepted only if the final uint8 prediction is exactly equal to
    the frozen historical path on the benchmark region.
    """
    h, w = dsm.shape
    coords = coords_for_shape(h, w)

    optical_gpu, dsm_gpu = prepare_gpu_tiles(optical, dsm)
    score = torch.zeros(
        (e51c.N_CLASSES, h, w),
        dtype=torch.float32,
        device=e51c.DEVICE,
    )

    with torch.inference_mode():
        for start in range(0, len(coords), BATCH):
            batch_coords = coords[start : start + BATCH]

            op = torch.stack(
                [
                    optical_gpu[:, y : y + e51c.PATCH, x : x + e51c.PATCH]
                    for y, x in batch_coords
                ],
                dim=0,
            ).contiguous()

            ds = torch.stack(
                [
                    dsm_gpu[y : y + e51c.PATCH, x : x + e51c.PATCH]
                    for y, x in batch_coords
                ],
                dim=0,
            ).contiguous()

            if model_name == "PH4k":
                net.set_sample_scales([1.0] * len(batch_coords))

            logits = net(op, ds)

            # Preserve the same patch order as the historical implementation.
            for output, (y, x) in zip(logits, batch_coords):
                score[:, y : y + e51c.PATCH, x : x + e51c.PATCH].add_(output)

            del op, ds, logits

    return torch.argmax(score, dim=0).to(torch.uint8).cpu().numpy()


def timed(fn, net, model_name, optical, dsm):
    reset_measurement()
    t0 = time.perf_counter()
    pred = fn(net, model_name, optical, dsm)
    seconds, peak_gib = finish_measurement(t0)
    return pred, seconds, peak_gib


def compare(reference, candidate):
    diff = int(np.count_nonzero(reference != candidate))
    return diff == 0, diff


def main():
    print("=" * 100)
    print("E51-C FAST-PATH BENCHMARK")
    print("=" * 100)
    print("tile:", TILE_ID)
    print("center region:", REGION, "x", REGION)
    print("patch:", e51c.PATCH)
    print("stride:", e51c.TEST_STRIDE)
    print("batch:", BATCH)
    print("dtype: FP32")
    print("NOTE: patch/stride/batch/model/input are frozen. Only data movement/score placement changes.")

    native = e51c.load_test_tile(TILE_ID)
    crop = center_crop(native, REGION)

    pp_net, _, _ = e51c.build_model("PP4k", e51c.PP_CKPT)
    ph_net, _, _ = e51c.build_model("PH4k", e51c.PH_CKPT)

    paths = [
        ("reference_cpu_input_cpu_score", infer_reference),
        ("gpu_input_cpu_score", infer_gpu_input_cpu_score),
        ("gpu_input_gpu_score", infer_gpu_input_gpu_score),
    ]

    summary = {
        "tile_id": TILE_ID,
        "region": REGION,
        "patch": e51c.PATCH,
        "stride": e51c.TEST_STRIDE,
        "batch": BATCH,
        "dtype": "float32",
        "models": {},
    }

    for model_name, net in (("PP4k", pp_net), ("PH4k", ph_net)):
        print()
        print("#" * 100)
        print(model_name)
        print("#" * 100)

        reference = None
        ref_seconds = None
        rows = []

        for path_name, fn in paths:
            pred, seconds, peak_gib = timed(
                fn,
                net,
                model_name,
                crop["optical"],
                crop["dsm"],
            )

            if reference is None:
                reference = pred.copy()
                ref_seconds = seconds
                equal = True
                diff_pixels = 0
            else:
                equal, diff_pixels = compare(reference, pred)

            speedup = ref_seconds / seconds
            row = {
                "path": path_name,
                "seconds": seconds,
                "speedup_vs_reference": speedup,
                "peak_allocated_gib": peak_gib,
                "prediction_equal_to_reference": bool(equal),
                "different_pixels": diff_pixels,
            }
            rows.append(row)

            print(
                f"{path_name:30s} | {seconds:8.3f}s | "
                f"speedup={speedup:5.2f}x | peak={peak_gib:5.2f} GiB | "
                f"same_pred={equal} | diff_pixels={diff_pixels}"
            )

        summary["models"][model_name] = rows

    candidate_paths = ["gpu_input_cpu_score", "gpu_input_gpu_score"]
    safe = []
    for path_name in candidate_paths:
        if all(
            next(
                r
                for r in summary["models"][model_name]
                if r["path"] == path_name
            )["prediction_equal_to_reference"]
            for model_name in ("PP4k", "PH4k")
        ):
            safe.append(path_name)

    summary["exact_prediction_safe_paths_on_benchmark"] = safe

    recommended = None
    if safe:
        def worst_speedup(path_name):
            return min(
                next(
                    r
                    for r in summary["models"][model_name]
                    if r["path"] == path_name
                )["speedup_vs_reference"]
                for model_name in ("PP4k", "PH4k")
            )

        recommended = max(safe, key=worst_speedup)

    summary["recommended_path"] = recommended
    summary["warning"] = (
        "Exact equality here is checked on one 2048x2048 region only. "
        "A candidate fast path may be used for diagnostic runs only after this gate passes. "
        "Historical batch-8 stride-64 results remain the frozen formal reference."
    )

    out_path = OUT / "benchmark.json"
    out_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print()
    print("=" * 100)
    print("EXACT SAFE PATHS:", safe)
    print("RECOMMENDED:", recommended)
    print("OUTPUT:", out_path)
    print("=" * 100)


if __name__ == "__main__":
    main()
