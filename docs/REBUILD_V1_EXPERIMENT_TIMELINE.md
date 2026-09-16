# REBUILD_V1 experiment purpose and timing timeline

Last updated: 2026-09-16
Timezone for server execution records: `UTC+08:00` (server displayed `CST`).

This file is the central index for **why an experiment was run, when it was run, what evidence it produced, and what decision followed**. It complements `docs/REBUILD_V1_EXECUTION_PLAN_20260915.md`; it does not replace the detailed README/CSV/JSON records.

## Timing rules

For new experiments, record:

- `started_at`: actual process launch time in ISO-8601 form with UTC offset;
- `completed_at`: actual successful completion time if available;
- `recorded_at`: time the result was written into the experiment record/Git history;
- `status`: `planned`, `running`, `complete`, `failed`, `aborted`, or `closed`;
- `time_source`: log timestamp, process start, queue timestamp, or other direct evidence.

Do **not** invent missing historical clock times. If only the date is known, record date precision. If completion is known only because a later gate observed a finished artifact, write `confirmed complete by ...` rather than estimating an end time.

---

## Historical evidence carried into REBUILD_V1

### E50 — historical modality-quality / reliability diagnostics

- **status:** closed historical/development evidence
- **purpose:** test whether the historical reliability gate behaves like a stable modality-quality estimator under Optical/DSM corruption.
- **main finding:** the old gate response was not reliably aligned with modality degradation; this motivated separating high-frequency strength, modality quality, and actual conditional utility.
- **timing:** historical; exact clock times are not reconstructed here.
- **role in REBUILD_V1:** motivation only; do not resume the legacy reliability-v2 route unless later gates justify it.

### E51-B — historical Grid-GSD same-step PP4k vs PH4k

- **status:** closed historical/development evidence
- **purpose:** compare PP4k and PH4k under jointly resampled raster grids while matching checkpoint step.
- **main finding:** PH4k retained a positive accuracy margin that generally widened as the synthetic grid became coarser, but the protocol also changes sampling grid, physical window coverage, and label rasterization.
- **timing:** completed before REBUILD_V1 freeze on 2026-09-15; exact clock time not reconstructed.
- **records:** `records/e51b_same_step_per_class_summary_20260915/`.
- **decision:** not sufficient to claim a physical-GSD mechanism.

### E51-C — fixed-grid information-degradation close-out

- **status:** complete / closed
- **purpose:** separate generic information/detail loss from historical Grid-GSD changes by degrading inputs and restoring them to the native grid while keeping labels/output coordinates unchanged.
- **execution date:** 2026-09-15 (date precision in retained records).
- **records:** `records/e51c_fixed_grid_information_degradation_20260915/`.
- **main finding:** joint x2 and DSM-only x2 did not show a PH-specific robustness advantage; DSM-only smoothing slightly improved both models, with PP improving more.
- **decision:** stop E51-C factor expansion; physical-frequency work becomes secondary and requires new-training `PH-correct` vs `PH-shuffled` control before revival.

---

## REBUILD_V1 framework and budget validation

### Split freeze — Train16 / Val2 / historical TEST6 separation

- **status:** complete
- **date:** 2026-09-15
- **purpose:** prevent the repeatedly exposed Potsdam TEST6 from selecting checkpoints or training budget.
- **split:** Train16 = `6_10,7_10,2_12,2_10,7_8,3_12,5_12,7_11,7_9,6_9,7_7,4_12,6_8,6_12,6_7,4_11`; Val2 = `3_11,5_10`.
- **record:** `configs/rebuild_v1/potsdam_split_seed20260915.json`.
- **decision:** all REBUILD_V1 development selection uses Val2 only; historical TEST6 is not loaded during training.

### R02 smoke gates — trainer / validation / checkpoint path

- **status:** complete, PASS
- **execution date:** 2026-09-15 (date precision)
- **purpose:** verify the unified REBUILD_V1 trainer, split isolation, deterministic short-run behavior, Val2 evaluation, and checkpoint path before a real budget pilot.
- **record:** `records/rebuild_v1_r02_smoke_gates_20260915/README.md`.
- **decision:** safe to launch the first complete-schedule R02 budget pilot.

### R02 complete-schedule budget pilot — 12k

- **status:** complete, PASS as a run; **not accepted as final budget**
- **started_at:** approximately `2026-09-15T22:11+08:00` (minute precision from retained process start display)
- **completed_at:** exact clock time not retained in the committed summary; confirmed complete by `2026-09-16T11:02:18+08:00` when the corrected diagnostics queue detected `summary.json`.
- **purpose:** determine whether a complete 12k LR schedule is sufficient before formal R01-R04 comparisons.
- **config:** `configs/rebuild_v1/r02_budget_pilot_12k.json`.
- **selection:** Val2 NoBoundary `mIoU_fg5`.
- **result:** best Val2 NoBoundary `mIoU_fg5 = 85.4135%` at step 12000; FullGT `mIoU_fg5 = 80.9842%`; `test6_loaded=false`.
- **decision:** do not freeze 12k because the best score occurs at the schedule endpoint and late improvement remains visible; run a fresh complete 16k schedule from initialization.

### R02 Val2 corruption screen — 12k best checkpoint

- **status:** complete
- **started_at:** after corrected queue start `2026-09-16T11:02:18+08:00`
- **completed_at:** before resume audit; entire diagnostics queue completed `2026-09-16T11:09:13+08:00`.
- **purpose:** measure absolute R02 sensitivity to mild modality degradation and artificial modality missing on Val2 before a true Optical-only control exists.
- **record:** `records/rebuild_v1_r02_corruption_screen_20260915/` and `records/rebuild_v1_r02_diagnostics_20260916/README.md`.
- **main result (NB mIoU_fg5):** clean 85.4135; DSM blur5 85.0769 (-0.3365 pp); DSM down2 85.1568 (-0.2567 pp); Optical blur5 84.2223 (-1.1912 pp); Optical down2 84.8649 (-0.5485 pp); DSM zero 50.6945 (-34.7190 pp).
- **decision:** R02 is relatively insensitive to the tested mild DSM degradation but highly dependent on DSM under artificial full-modality removal. This is **not yet harmful-fusion evidence**; matched R01 Optical-only Fusion Gain is still required.

### REBUILD_V1 resume exactness audit

- **status:** complete, EXACT PASS
- **execution window:** within corrected diagnostics queue `2026-09-16T11:02:18+08:00` to `2026-09-16T11:09:13+08:00`.
- **purpose:** verify that save/load plus RNG restoration reproduces the uninterrupted deterministic trajectory exactly.
- **protocol:** uninterrupted 40 optimizer steps vs 20 steps + save/load/RNG restore + 20 steps.
- **result:** loss exact, max loss difference 0.0, model-state SHA256 exact, optimizer-state SHA256 exact.
- **record:** `records/rebuild_v1_resume_exactness_20260915/result.json`.
- **decision:** the current deterministic resume path is accepted for REBUILD_V1 engineering use.

### R02 complete-schedule budget pilot — 16k

- **status:** **running**
- **started_at:** approximately `2026-09-16T11:19+08:00` (minute precision from process start display)
- **completed_at:** pending
- **purpose:** test whether extending the complete LR decay horizon from 12k to 16k removes the endpoint-improvement ambiguity seen in the 12k pilot.
- **config:** `configs/rebuild_v1/r02_budget_pilot_16k.json`.
- **controlled change vs 12k:** scheduler/stop horizon 16000 instead of 12000; warmup remains 1200; split/model/optimizer/augmentation/validation protocol remain matched.
- **decision rule:** inspect the 13k-16k Val2 region. Freeze 16k only if the late region is stable/plateaued and no material sustained endpoint improvement remains.
- **next decision:** if budget is frozen, proceed to formal `R01 -> R02 -> R03 -> R04`.

---

## Formal REBUILD_V1 experiment purposes after budget lock

| ID | Status | Purpose |
|---|---|---|
| R01 | planned | Train a genuine Optical-only baseline to establish what Optical alone can do and enable matched Fusion Gain. |
| R02 | budget pilot running; formal run pending | Matched clean Optical+DSM baseline; measure clean DSM fusion gain. |
| R03 | planned | Train with simple quality corruption Q; test how much degraded-modality robustness is solved by ordinary corruption training. |
| R04 | planned | Train with modality dropout D; test how much missing-modality robustness is solved by a simple strong baseline. |
| R05 | conditional | Q+D only if R03/R04 leave a meaningful residual gap. |
| M1/M2 | gated | Selective DSM fusion only if harmful fusion is supported and simple Q/D baselines leave a stable residual gap. |
| PH-correct / PH-shuffled | secondary / gated | Physical-frequency route only if new-training controls show a contribution from correct physical correspondence beyond generic interpolation/resampling regularization. |

## Core causal question

REBUILD_V1 is not primarily a search for another frequency module. Its main question is:

> Does DSM provide positive fusion gain under clean conditions but become harmful as DSM quality or availability degrades, and can simple robust training prevent that harmful fusion?

The decisive quantity is **Fusion Gain = matched dual-modal performance - matched Optical-only performance under the same input condition**, reported together with clean/corrupted absolute accuracy, corruption drop, FullGT/NoBoundary metrics, per-class IoU, and raw confusion matrices.
