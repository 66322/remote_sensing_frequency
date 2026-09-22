# Current Project Status

- Updated: 2026-09-22
- Active branch: `rebuild-v1-protocol-20260915`
- Current line: completed reliability-aware distillation audit; D7 no-training data/error audit prepared
- Dataset/split: ISPRS Potsdam Train16 -> Val2 (`3_11`, `5_10`)
- Primary metric: Val2 `mIoU_fg5(noboundary)`
- Historical TEST6: prohibited for training, selection and current diagnostics
- Execution device: physical GPU 0 only (`CUDA_VISIBLE_DEVICES=0`)

Evidence provenance: core results plus compact B2/B3/B4 transcriptions are committed. The compact files were reconstructed from user-supplied validated server output; original logs, full CSV files, confusion matrices and checkpoints remain on the server and take precedence if a discrepancy is found.

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

## B4 completed seed17 replication

B4 ran C17, R05_KD17 and KD17 with matched seed17 initialization, augmentation,
budget and selection protocol. The queue completed all 12 stages from
2026-09-21 17:22:07 to 2026-09-22 01:29:52 +08:00. All formal runs reached
4000 steps and TEST6 was not loaded.

Val2 NoBoundary `mIoU_fg5` (%):

| Arm | clean | DSM down8 | DSM zero |
|---|---:|---:|---:|
| C17 | 86.6027 | 84.9647 | 83.3285 |
| R05_KD17 | 86.1756 | 84.9972 | 83.1646 |
| KD17 | 86.6258 | 85.2065 | 83.2083 |

KD17 is above R05_KD17 by +0.2093 pp down8 and +0.0438 pp zero, so the global
degradation direction from seed42 repeats. Against C17, however, KD17 is 0.1202 pp
lower on DSM-zero.

In paired local damaged regions, KD17 has a -3.3120 pp local-missing drop and a
-1.1831 pp local-down8 drop. These are respectively 0.2855 and 0.0372 pp worse
than R05_KD17. Both local directions reverse the seed42 ordering. The documented
B4 decision gate therefore fails.

Compact evidence: `records/rebuild_v1_b4_seed17_compact_20260922/` and
`docs/experiments/B4_SEED17_REPLICATION_20260921.md`.

## Current conclusion boundary

Supported:

- SafeMaxConfidence teacher selection shows a small, directionally repeated global
  advantage over an ordinary R05 teacher under down8 and zero DSM in seeds 42 and 17;
- the effect is not explained solely by continued CE training under down8;
- local complete DSM absence remains unresolved;
- SAFE and AVG_KD have no consistent reason to continue unchanged.

Not supported:

- a cross-seed local reliability-teacher advantage;
- a generally superior model over CE, because KD17 is below C17 on DSM-zero;
- a learned missing-modality detector, explicit Optical fallback or deployment-ready
  router;
- independent-dataset, held-out-test or population-level significance claims.

The current SafeMaxConfidence distillation implementation is closed as the proposed
main method. B1–B4 may be retained as mechanism, ablation and negative-result
evidence. A new main-method experiment requires a changed reliability design and a
new frozen evaluation source rather than another identical Val2 rerun.

D7 is the immediate diagnostic gate. It measures class and crop exposure on
Train16 and evaluates existing R01/R05 checkpoints by class, connected-object size
and true semantic boundary. D7 does not train or select a new model, and its Val2
flags remain exploratory. Protocol:
`docs/protocols/D7_DATA_SCALE_BOUNDARY_AUDIT.md`.
