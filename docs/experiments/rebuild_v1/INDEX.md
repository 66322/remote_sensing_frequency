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
| Post-D30 B/C/F | B6/6原件已收；10月5日00:26原18项COMPLETE，C最终原件已收；F四项实际SKIPPED_GATE | 对应/增强、缺失迁移、条件频率 | B3 gate=False；C2双側门槛False，N6实际跳过；[C原件验收](../POST_C_N1_RESULTS_20261005.md) | [报告](../POST_D30_AB_RESULTS_20261004.md) |

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

[Post-A/B候选池](../../protocols/POST_AB_FOLLOWUP_PLAN_20261004.md)：用户要求扩展规划，2类评估、6类训练研究、最多26配置；2026-10-04已授权条件排队；最后观测10月5日07:21 N1四组COMPLETE、固定gate=False、原件已验收；N2六组已登记于独立新目录，实际进度待查询，N3—N5共13项仍预约，N6三项SKIPPED_GATE，不修改原C/F门槛。

[Post-A/B队列包](../../protocols/POST_AB_QUEUE_EXECUTION_20261004.md)：CPU8项检查PASS；N1四组原件已独立验收，固定gate=False；设计登记记录records/research_post_ab_queue_design_20261004/queue_template.json。

## 记录完整性

[2026-10-04归档核对](../GITHUB_RECORD_COMPLETENESS_20261004.md)：10份清单5726项载荷均存在且大小匹配；D30逐tile矩阵、C最终原件及F实际跳过待接。部分早期历史实验仍仅有回报/紧凑记录；清单完整不代表全量指标已独立验收。

## 2026-10-05最新阶段

[N1完成回报与接续](../POST_AB_N1_COMPLETION_OBSERVATION_20261005.md)：四组8000步完成；N1-3对N1-1 +2.789492pp、对N1-2 −0.881059pp，固定门槛False（用户回报，原件待验收）。控制器按设计退出；N2匹配基座为N1-2，19项预约不等于可执行，N6三项跳过。

## C/N1验收与N2接续（2026-10-05）

[C/N1最终报告](../POST_C_N1_RESULTS_20261005.md)：十组20份summary整数与绑定复核PASS，C2双侧门槛及N1-3门槛False；N2固定N1-2基座。[N2可执行协议](../../protocols/POST_AB_N2_EXECUTION_20261005.md)和六组worker/controller已实现、CPU8项PASS，服务器登记回报已收，实际训练状态待查询，不声称正在运行。旧N1预约不改写，新N2目录是实际执行状态来源。

2026-10-05 N2[登记回报](../../../records/research_post_ab_followup_n2_20261005T085829_3456726/user_reported_registration_20261005.json)已收：目录时间标记08:58:29，PID3456909，EXECUTABLE=6；无首步/存活查询回报。下一步只读状态与日志，不重复登记。


## 2026-10-05 N2控制器技术故障

最后服务器观测（用户回传）：2026-10-05T08:58:59.848681+08:00，N2控制器PID3456909已退出，QUEUE=CONTROLLER_INTERRUPTED。N2-0已派发到GPU0（worker PID3457210），其实际存活/训练步数待核对；不能把旧step=0快照当成当前进度。N2-1—5尚待派发。原科学执行提交86b6a70e5c3482314986fb1259e2fccbd0a5a38b保留。故障为per_job_timeout_hours=null被直接乘3600；这是控制器技术失败，不是N2科学负结果。控制器专用修复和安全接管工具已发布，尚无服务器恢复执行回报。先接管已有worker或验收绑定完成记录；已退出且未有效完成则HOLD、输出日志，不自动重训。不重复登记N2，不重启原C/N1。

[控制器修复说明](../POST_AB_N2_CONTROLLER_REPAIR_20261005.md)：CPU恢复11项及原N2八项通过；修复单独安装、科学快照保留，不把派发或CPU检查记为实验完成。


## 2026-10-05 N2接管回报

最后服务器接管回报（用户终端）：2026-10-05，修复目录时间标记09:17:55（不是queue observed_at或精确训练进度时间）。修复控制器PID3467202已登记，目录controller_repair_20261005T091755_3467074；日志出现POST_AB_ADOPT 0 N2-0 3457210，确认接管原GPU0 worker，没有重启N2-0。ACCEPT_COMPLETE=[]，没有新增完成回报。安装器启动前恢复CPU检查已通过（按登记前执行链推断，未收单独测试日志）；本次只收到控制器日志首条ADOPT，尚未收到后续状态、N2-0实际训练步数或N2-1启动记录，不声称两卡训练已确认。原科学快照86b6a70e5c3482314986fb1259e2fccbd0a5a38b与修复9b196a204e6a45cb54244b4deb5437ff44bd074e分开保留。下一步只读查询状态/进度/日志，不重复登记或再次运行修复。

接管原件见[user_reported_controller_adoption_20261005.json](../../../records/research_post_ab_followup_n2_20261005T085829_3456726/user_reported_controller_adoption_20261005.json)。08:58故障记录保留为历史；当前下一步为查询已登记的修复控制器，不重复安装。


## 2026-10-05 09:21 N2两卡实际训练回报

最后服务器观测（用户终端回传）：2026-10-05T09:21:05.606873+08:00，QUEUE=RUNNING_N2，修复控制器PID3467202 LIVE=True。GPU0 N2-0原worker PID3457210 LIVE=True，training 940/8000（progress观测09:20:52.566194，1.309439秒/训练步）；GPU1 N2-1新worker PID3467394 LIVE=True，training 60/8000（progress观测09:20:47.378619，1.347363秒/训练步）。N2-2—5 PENDING，两卡各一个worker；两组均已加载12/12训练tile。日志确认ADOPT原N2-0、CONDITIONS_PASS 32、HANDOVER READY COMPLETE和START N2-1，原N2 CPU8项复查PASS。接管后两卡实际训练已确认，未重训N2-0，暂无N2完成或精度结果。科学快照86b6a70e5c3482314986fb1259e2fccbd0a5a38b、修复9b196a204e6a45cb54244b4deb5437ff44bd074e与原plan保留。继续已有队列，只读观察，不重复登记或重启。

[原始回报转录](../../../records/research_post_ab_followup_n2_20261005T085829_3456726/user_reported_running_20261005T092105.json)。首段吞吐只覆盖训练，不包括4000/8000验证和末尾评价；训练启动与工程恢复不等同机制门槛通过。


## 2026-10-05后续规划（助手建议，尚未激活）

根据用户本次要求，已核对相关原始论文并形成[条件实验规划](../../protocols/POST_N2_EVIDENCE_LED_PLAN_20261005.md)：N2完成后先E0空间诊断与E1内容相关缺失，建议E1触发N5四组优先；N3五组需区域问题证据，N4四组需实际条件更新暴露证据。新增E2物理缺失×标记可靠性只作无训练诊断。潜在训练仍最多13组，不默认全部运行。当前每批两侧own CE和抽样非零梯度记录不足以证明弱侧更新缺口；不重做D25分头/PCGrad或D8类别采样。

上述是建议优先级与待冻结设计，不是N3/N4/N5已实现/排队，也未修改旧N2协议、旧预约或当前队列。最后服务器观测仍09:21:05，未获得新的精度回报。研究主线、旁支角色与C/N1失败去留不变；无新增训练、seed或Test6访问。
