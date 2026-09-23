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
| B4 | seed17 C/R05_KD/KD replication | complete; documented gate failed | `records/rebuild_v1_b4_seed17_compact_20260922/` |
| D7 | data, scale and semantic-error audit | complete | `docs/experiments/D7_RESULTS_20260922.md` |
| D8 | seed42 C/A/S sampling screen | complete; gate failed | `docs/experiments/D8_RESULTS_20260922.md` |
| D9 | frozen-expert DSM benefit diagnostic | D9A complete; full gate unevaluated | `docs/protocols/D9_DSM_BENEFIT_DIAGNOSTIC.md` |
| D9A | direct confidence/entropy/disagreement benefit audit | complete; entropy ranking positive, disagreement interaction negative | `docs/experiments/D9A_RESULTS_20260923.md` |
| D9A local-down8 fix1 | correct degraded-DSM routing for seeds 42/17 | complete; zero failures; ranking unchanged | `records/rebuild_v1_d9a_compact_20260923/user_reported_local_down8_fix1.json` |
| D9A entropy route | safe entropy versus safe confidence routing with frozen experts | complete; 4 wins, 10 losses, 2 ties | `docs/experiments/D9A_ENTROPY_ROUTE_RESULTS_20260923.md` |
| D9B source audit | locate independent labelled scenes for benefit prediction | repository audit complete; server inventory pending | `docs/current/D9B_SOURCE_STATUS_20260923.md` |
| D9B decision-benefit screen | semantic/frequency/expert evidence on decision-changing pixels | complete; six-score gate failed | `docs/experiments/D9B_RESULTS_20260923.md` |
| D10 selective DSM benefit | learned decision target with calibrated abstention | design frozen; independent source pending; no run | `docs/protocols/D10_SELECTIVE_DSM_BENEFIT.md` |

The JSON registry is the machine-readable authority. This index is the
human-readable navigation layer.
