# REBUILD_V1 Experiment Index

本索引列实验事实，不决定论文主线。路线角色与去留原则见[研究决策说明](../../current/RESEARCH_DECISION.md)，执行待办见[下一步](../../current/NEXT_EXPERIMENT.md)。C1是旁支候选；已关闭方案保持原门槛。

## 2026-10-04近期补全

本表逐轮说明目的、结论和证据范围，详细内容见[已完成实验整理](../COMPLETED_EXPERIMENTS_HANDOFF_20261004.md)。以下状态是带时间戳的历史观测，不是实时服务器查询。

| 实验 | 状态 | 做了什么 | 得到什么结论/边界 | 证据 |
|---|---|---|---|---|
| D23 | 8/8完成 | 冻结专家＋语义/频率/效用门控是否优于强融合 | TSF综合比M0_safe低0.148998pp；减害同时丢失纠错，全部机制门槛未过。已知DSM缺失回退为工程能力。 | [报告](../D23_EIGHT_ARM_RESULTS_20261001.md) |
| D24 | 15/15技术完成；2项Pair消融无效 | 适配、增强、配对约束和语义/KD | 部分解冻与普通增强是强基线。A1/A3损失开关未启用，不能当Pair负结果；其他比较保留。 | [报告](../D24_REVIEW_AND_PAIR_CORRECTION_20261002.md) |
| D25 | 8/8完成 | 修正Pair、状态分头、完整/缺失梯度投影 | 四项预设机制筛选均未过；真实Pair已启用，采样梯度不支持全局冲突是当前主要瓶颈。 | [报告](../D25_MISSINGNESS_RESULTS_20261002.md) |
| D26 | 9/9完成 | 双向特征交互、容量及语义/频率打乱对照 | 普通B0融合对RGB综合+0.690973pp；XSF对B0仅+0.156829pp，未过增量与双侧保留门槛。 | [报告](../D26_COMPLETE_D27_FAILURE_REVIEW_20261003.md) |
| D27原队列 | 10项step0技术失败 | 安全/全局/局部/类别路由 | KeyError treatment导致未训练，不构成科学负结果；修复队列另记。 | [报告](../D26_COMPLETE_D27_FAILURE_REVIEW_20261003.md) |
| D27修复队列 | 10/10完成 | 保护与恢复、动态专家、局部/类别路由 | 保护＋恢复相对匹配对照损失约1.77—1.89pp；更多DSM独有信息保留伴随RGB原正确损失，四项机制门槛均未过。 | [报告](../D27_FINAL_REVIEW_20261003.md) |
| D28 | 7/7模型评价完成；无新训练 | 相同边际损伤下，共同受损与独立受损 | B0独立−共同仅+0.014570pp，未过0.3pp；本轮不支持共同受损主假设，未触发原D29。 | [报告](../D28_FINAL_REVIEW_20261003.md) |
| D30 | 6/6完成（4训练＋2重放，另复用S0/S1） | 保护/恢复损失拆解、面积/像素归一化、固定checkpoint路由干预 | P对S0综合+0.041182pp；R−2.013409pp；PR_area−0.064718pp；PR_pixel−1.291674pp。四项继续门槛均False；归一化缓解损失但未建立贡献。 | [报告](../D30_COMPLETED_REVIEW_20261004.md) |
| Post-D30 A | 6/6完成、原件已收 | 对齐范围/错配/权重 | A2对A0仅+0.101643pp、低于A1/A3，gate=False；关键组整数复核PASS | [报告](../POST_D30_AB_RESULTS_20261004.md) |
| Post-D30 B/C/F | B6/6原件已收；10月5日后继日志READY COMPLETE，原C最终原件待接；F gate=False、实际标记原件待接 | 对应/增强、缺失迁移、条件频率 | B3对B1几何+0.021260pp、对B4−0.012852pp且DSM harm增加，gate=False；F实际跳过标记待确认 | [报告](../POST_D30_AB_RESULTS_20261004.md) |

## 历史索引（保留原证据）

| ID | Purpose | Status | Primary evidence |
|---|---|---|---|
| D23 B engine admission | frozen expert8/gate16 single backward, 8-arm smoke and full-image profile | originals uploaded to GitHub; 8 hashes/107 matrices and CPU22 checks passed; formal budget subsequently completed; see D23 eight-arm review | [audit](../D23_B_ENGINE_GITHUB_AUDIT_20261001.md) |
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

## 后续规划（不计入已运行实验）

[Post-A/B候选池](../../protocols/POST_AB_FOLLOWUP_PLAN_20261004.md)：用户要求扩展规划，2类评估、6类训练研究、最多26配置；2026-10-04已授权条件排队；最后观测10月5日07:21 N1四组COMPLETE、固定gate=False；N2—N5共19项预约，N6三项SKIPPED_GATE；原件待接，不修改原C/F门槛。

[Post-A/B队列包](../../protocols/POST_AB_QUEUE_EXECUTION_20261004.md)：CPU8项检查PASS；N1四组已有服务器COMPLETE回报，原始结果待独立验收；设计登记记录records/research_post_ab_queue_design_20261004/queue_template.json。

## 记录完整性

[2026-10-04归档核对](../GITHUB_RECORD_COMPLETENESS_20261004.md)：10份清单5726项载荷均存在且大小匹配；D30逐tile矩阵、C最终原件及F实际跳过待接。部分早期历史实验仍仅有回报/紧凑记录；清单完整不代表全量指标已独立验收。

## 2026-10-05最新阶段

[N1完成回报与接续](../POST_AB_N1_COMPLETION_OBSERVATION_20261005.md)：四组8000步完成；N1-3对N1-1 +2.789492pp、对N1-2 −0.881059pp，固定门槛False（用户回报，原件待验收）。控制器按设计退出；N2匹配基座为N1-2，19项预约不等于可执行，N6三项跳过。
