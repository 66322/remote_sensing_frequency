# Current Project Status

- Updated: 2026-09-21
- Active branch: `rebuild-v1-protocol-20260915`
- Current line: reliability-aware distillation under RGB–DSM degradation
- Dataset/split: ISPRS Potsdam Train16 -> Val2 (`3_11`, `5_10`)
- Primary metric: Val2 `mIoU_fg5(noboundary)`
- Historical TEST6: prohibited for training, selection and current diagnostics
- Execution device: physical GPU 0 only (`CUDA_VISIBLE_DEVICES=0`)

Evidence provenance: core results and compact B2/B3 transcriptions are committed. The B2/B3 compact files were transcribed from user-supplied server terminal output; original logs, CSV files, confusion matrices and checkpoints remain on the server and take precedence if a discrepancy is found.

## Completed core results

| ID | Meaning | FullGT mIoU_fg5 | NB mIoU_fg5 | Status |
|---|---|---:|---:|---|
| R01 | true Optical-only | 80.6883 | 85.3713 | complete |
| R02 | clean Optical+DSM | 81.8483 | 86.2016 | complete |
| R03 | quality-corruption training Q | 82.1069 | 86.5251 | complete |
| R04 | modality-dropout training D | 81.6042 | 85.9818 | complete |
| C-OO | Optical+Optical capacity control | 81.8281 | 86.3548 | complete |
| R05 | Optical+DSM with Q+D | 82.5147 | 87.0485 | complete |
| C-OO-QD | Optical+Optical with matched Q+D | 81.6670 | 86.1969 | complete |

These are seed42 results on the two-tile Val2 development split. They are not multi-seed or held-out test conclusions.

## Previously completed supporting evidence

| ID | Clean NB mIoU_fg5 | DSM zero | DSM down8 | Interpretation |
|---|---:|---:|---:|---|
| A1 no Optical dropout | 86.4066 | 81.2529 | 85.7454 | negative fallback ablation |
| A2 DSM dropout 20% | 85.7936 | 83.9292 | 84.8006 | fallback/clean trade-off |
| R05 seed17 | 85.8600 | 83.2120 | 84.4839 | independent-seed base model |
| C-OO-QD seed17 | 85.6440 | 83.0267 | 77.8835 | matched second-stream control |

R01 seed17 reaches 85.8366 clean NB mIoU_fg5. R05 exceeds it by only 0.0234 pp on clean seed17, while retaining a 6.6004 pp down8 advantage over C-OO-QD. Earlier local diagnostics also found that R05 does not exceed C-OO-QD inside locally missing regions, whereas it retains value under local down8. These observations motivated reliability-aware distillation rather than another unconditional fusion module.

## B1/B2 completed seed42 controls

All values below are Val2 `mIoU_fg5(noboundary)`, in percent.

| Arm | Role | clean | DSM down8 | DSM zero |
|---|---|---:|---:|---:|
| C | matched CE continuation | 86.9976 | 85.6900 | 83.0949 |
| KD | SafeMaxConfidence teacher distillation | 87.2223 | 86.2175 | 83.7867 |
| SAFE | KD plus explicit Optical consistency | 87.2998 | 86.3802 | 83.6187 |
| R05_KD | ordinary dual-modal R05 teacher | 87.4440 | 85.9955 | 83.6299 |
| AVG_KD | averaged R01/R05 teacher | 87.2595 | 86.0029 | 83.5725 |

KD exceeds C by +0.2247 pp clean, +0.5275 pp down8 and +0.6918 pp DSM-zero. SAFE does not consistently exceed KD. R05_KD exceeds KD by +0.2217 pp clean but is lower by 0.2220/0.1568 pp under down8/zero. Therefore the current seed42 evidence separates a reliability-aware teacher effect from generic distillation, but does not establish a universal gain.

Compact evidence: `records/rebuild_v1_b2_b3_compact_20260921/` and `docs/experiments/B2_B3_RESULTS_20260921.md`.

## B3 paired local diagnostic

B3 compares corrupt and clean predictions on the same pixels. KD has a smaller metric drop than R05_KD in all eight tile x corruption-family x region comparisons. The improvement in drop ranges from 0.0192 to 3.2908 pp. This supports reduced transfer of unreliable DSM-teacher predictions within seed42.

The absolute comparison against CE remains mixed. For local missing, pooled KD is only +0.0551 pp better than C in the damaged region and 2.6510 pp worse at the boundary. For local down8, KD improves the pooled damaged and boundary drops by 0.3326 and 1.8050 pp. Boundary results are secondary diagnostics because the thin regions have volatile class support.

## Current conclusion boundary

Supported as seed42 stage evidence:

- reliable teacher-target selection is preferable to an ordinary R05 teacher under the evaluated DSM degradations;
- generic continuation alone does not explain all global robustness gains;
- local complete DSM absence remains the harder unresolved condition;
- SAFE and AVG_KD show no consistent reason to continue as primary arms.

Not supported:

- a learned missing-modality detector or an inference-time Optical-only fallback;
- robustness under every local region, seed, dataset or real sensor failure;
- a held-out test conclusion or final thesis claim before seed17 replication.

## Active work — B4 seed17 replication

Last observed from the user-supplied launcher log at 2026-09-21 17:25:17 +08:00: the queue had completed `C17_SMOKE` and started `C17_TRAIN` on physical GPU 0 (NVIDIA H100 80GB HBM3). This is a historical observation, not live monitoring.

B4 contains only the three necessary independent arms: C17, R05_KD17 and KD17. It tests whether the seed42 reliability-teacher direction reproduces under seed17 while keeping the R05 seed17 initialization, 4k continuation budget, augmentation mixture and selection protocol matched.

- Queue root: `records/rebuild_v1_b4_seed17_20260921/`
- Launcher log: `records/rebuild_v1_b4_seed17_20260921_launcher.log`
- PID file: `records/rebuild_v1_b4_seed17_20260921.pid`
- Started: 2026-09-21 17:22:07 +08:00
- Expected duration: about 8–9 hours, so the planning estimate is 2026-09-22 01:20–02:20 +08:00
- Hard launcher limit: 12 hours, approximately 2026-09-22 05:22 +08:00

Completion requires successful per-arm stages, expected step 4000, `test6_loaded=false`, the final summary, and `QUEUE COMPLETE`; elapsed-time prediction alone is not proof of completion.
