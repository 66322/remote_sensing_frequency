# REBUILD_V1 Experiment Index

| ID | Purpose | Status | Primary evidence |
|---|---|---|---|
| R01 | true Optical-only baseline | complete | `records/rebuild_v1_r01_formal_16k_20260916/` |
| R02 | clean dual baseline and 16k budget freeze | complete | `records/rebuild_v1_r02_budget_16k_20260916/` |
| R03 | quality-corruption baseline | complete | `records/rebuild_v1_r03_robust_eval_20260916/` |
| R04 | modality-dropout baseline | complete | `records/rebuild_v1_r04_robust_eval_20260916/` |
| Core Matrix | R01-R04 unified comparison | complete | `records/rebuild_v1_core_matrix_20260917/` |
| C-OO | Optical+Optical capacity control | complete | `records/rebuild_v1_c_oo_formal_16k_20260918/` |
| R05 | Q+D Optical+DSM | complete | `records/rebuild_v1_r05_robust_eval_20260918/` |
| C-OO-QD | matched Q+D capacity control | complete | `records/rebuild_v1_c_oo_qd_formal_16k_20260918/` |
| C-OO-QD Robust | matched global robustness evaluation | complete | `records/rebuild_v1_c_oo_qd_robust_eval_20260918/` |
| D1-D3 | local missing, shift and local down8 | reported complete; originals pending | `docs/current/PROJECT_STATUS.md` |
| A1/A2 | dropout ablations | reported complete; originals pending | `docs/current/PROJECT_STATUS.md` |
| Seed17 | R01/R05/C-OO-QD replication | reported complete; originals pending | `docs/current/PROJECT_STATUS.md` |
| D4-D6 | expert complementarity and routing | reported complete; originals pending | `records/rebuild_v1_handoff_20260920/user_reported_snapshot.json` |
| B1 | seed42 CE/KD/SAFE 4k continuation | reported complete; compact transcription committed | `records/rebuild_v1_b2_b3_compact_20260921/global_metrics.csv` |
| B2 | seed42 R05-teacher and average-teacher controls | reported complete; compact transcription committed | `docs/experiments/B2_B3_RESULTS_20260921.md` |
| B3 | paired local damaged/boundary diagnostic | reported complete; compact transcription committed | `records/rebuild_v1_b2_b3_compact_20260921/paired_family_metrics.csv` |
| B4 | seed17 C/R05_KD/KD replication | running as last observed | `docs/current/HANDOFF.md` |

The JSON registry is the machine-readable authority. This index is the
human-readable navigation layer.
