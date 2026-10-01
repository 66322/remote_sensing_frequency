# REBUILD_V1 Experiment Index

本索引列实验事实，不决定论文主线。路线角色与去留原则见[研究决策说明](../../current/RESEARCH_DECISION.md)，执行待办见[下一步](../../current/NEXT_EXPERIMENT.md)。C1是旁支候选；已关闭方案保持原门槛。

| ID | Purpose | Status | Primary evidence |
|---|---|---|---|
| D23 B engine admission | frozen expert8/gate16 single backward, 8-arm smoke and full-image profile | originals uploaded to GitHub; 8 hashes/107 matrices and CPU22 checks passed; formal budget pending | [audit](../D23_B_ENGINE_GITHUB_AUDIT_20261001.md) |
| Post-D21 final and mixed follow-up | completed 42 A/B/C/D cells and four mixed-degradation C0/C1 cells | user-reported 42/42 and 4/4 complete; both integer audits PASS; single-seed development evidence | `docs/experiments/POST_D21_FINAL_AND_MIXED_FOLLOWUP_RESULTS_20261001.md` |
| Post-D21 A/B/C early analysis | 36/42 completed jobs, paired development comparisons while D continued | server-pasted early snapshot; integer audit PASS; not final D result | `docs/experiments/POST_D21_EARLY_AB_C_RESULTS_20260930.md` |
| Post-D21 mixed-degradation follow-up | paired C0/C1 under mixed scale and blur, four E cells, separate queue | 4/4 complete and audited per user log | `docs/protocols/POST_D21_MIXED_DEGRADATION_FOLLOWUP_20260930.md` |
| Post-D21 throughput probe | one-GPU F2 training and train-tile inference throughput; four microbatch/accumulation combinations | short probe complete; raw JSON and GPU telemetry archived; not accuracy evidence | `docs/experiments/POST_D21_THROUGHPUT_PROBE_RESULTS_20260929.md` |
| Post-D21 day portfolio | adaptation, conditional DSM residuals, joint LR restoration and factorial interaction | main 42/42 complete and audited; eight reserve excluded from frozen scope, four studied separately later | `docs/protocols/POST_D21_MULTIDIRECTION_DAY_PLAN_20260929.md` |
| D22 original draft | RGB-anchored fixed Sobel gate | superseded before implementation; no run | `docs/protocols/D22_STRUCTURE_ALIGNED_DSM_RELIABILITY_DRAFT_20260929.md` |
| D21 | matched fine-scale height and low/high frequency controls; 32 jobs on two datasets and two seeds | effective 32/32 complete and archived; F2 accuracy and missing-DSM safety gates failed | `docs/experiments/D21_DETAIL_FREQUENCY_RESULTS_20260929.md` |
| D20 | independent source acceptance and matched external P0/P1/P2 baselines | revised GAMUS three-city sample content passed; nine HDF5 files have no root/image attributes, source/geographic acceptance pending; US3D terms pending; Vaihingen seed42 per-tile gate failed, no automatic seed17 | `docs/experiments/D20_GAMUS_STAGE_A_SOURCE_AUDIT_RESULTS_20260928.md`; `docs/experiments/D20_GAMUS_SAMPLE_METADATA_RESULTS_20260928.md`; `docs/experiments/D20_VAIHINGEN_SEED42_RESULTS_20260928.md` |
| D18 seed17 replication | matched frozen-DINO P0/P1/P2 and paired error analysis across seeds42/17 | complete; originals archived and offline-audited; P2 passes both seeds with DSM absence cost | `docs/experiments/D18_REPLICATION_RESULTS_20260928.md` |
| D18/D19 | single-seed pretrained adapters and intervention structures | 8/8 complete, originals archived and offline-audited; P2 seed42 candidate; C2/C3 fail | `docs/experiments/D18_D19_RESULTS_20260928.md` |
| D16/D17 | intervention consistency and geometry auxiliary supervision; matched controls | 16/16 reported complete; archive audit passed; A2/B1 gates failed | `docs/experiments/D16_D17_RESULTS_20260927.md` |
| D14 | inference-only DSM-content sensitivity of frozen D13 heads | user-reported complete; sensitivity found, no benefit gate | `docs/experiments/D14_RESULTS_20260926.md` |
| D13 | trainable RGB-anchored DSM residual and risk surrogate | user-reported Stage 1 complete; two-seed gate failed; Stage 2 skipped | `docs/experiments/D13_RESULTS_20260925.md` |
| D11 | supervised benefit/harm probe with off-Val2 calibration | user-reported complete; gate failed | `docs/experiments/D11_RESULTS_20260923.md` |
| D12 | deep decoder context, frequency and capacity screen | user-reported complete; gate failed | `docs/experiments/D12_RESULTS_20260924.md` |
| D10M | amplitude-preserving spatial perturbation and harm/rescue | reported complete; fixed-score gate failed | `docs/experiments/D10M_RESULTS_20260923.md` |
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

Post-D21 A/B/C/D 42/42 and mixed E 4/4 are server-reported complete; integer audits PASS.
The C0/C1 tile-risk re-audit also passed. See
`docs/experiments/POST_D21_FINAL_AND_MIXED_FOLLOWUP_RESULTS_20261001.md` and
`docs/experiments/POST_D21_MIXED_TILE_RISK_RESULTS_20261001.md`.
