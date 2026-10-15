# Phase2.4验收收口：新增禁止重复项（2026-10-15）

- 原运行research_phase24_protected_20261014T193915_2149100及上传76ae973b已完成，不重复登记、训练、推理或上传。
- calibrated/probe原门禁均False；T1/T2/T3未派发，不为凑齐四头补跑。T0 4k为轨迹、8k为主端点，不择优年龄或自动延长。
- 不通过修改参考、去掉不利损坏、改保护线或将stump提升为事后主候选来倒写成功。T0也有DSM方向损伤。
- 不根据旧Post-AB/Post-D30 registry运行提示恢复历史队列；当前动作由2026-10-15交接和下一步决定。
- 不自动增加训练seed/新专家或访问Test6/held4/final。A/B问题尚未选定、无新GPU队列授权。

[完整报告](../experiments/PHASE_24_ACCEPTANCE_AND_ROUTE_REVIEW_20261015.md)。以下历史条目保留供查重，不作为当前运行指令。

---

# D23新增禁止重复规则（2026-10-01）

新对话先遵守[执行约定](../protocols/EXECUTION_CONTRACT.md)。D23-A、CPU检查、双卡工程smoke、双卡预算及相应原件校验已完成；工程证据d3829b6、预算证据54e19cd。不得因换对话/电脑重跑它们。保留历史失败日志不代表失败仍未修复（launcher cwd已在b02bb7b修复）。

正式队列已启动并进行nohup接续，见[交接](HANDOFF.md)。历史“等待启动”“先Ctrl+C再nohup”已过期。禁止再次停机/重复启动，不以GPU利用率低自动提高有效batch、精度或训练步数。新证据、代码/环境/数据实质变化只验证受影响范围；结果原件必要核验不等于重跑实验。

以下为保留的历史规则与背景，其旧状态描述不覆盖当前交接：

# 不可重复事项与适用边界

2026-10-01澄清：[研究定位](RESEARCH_DECISION.md)允许换解法、换交叉问题或换方向。下文关闭的是具体已测试方案及原门槛，不能扩大解释为所有频率/语义可靠性问题被否定，也不能因允许探索而原样重跑失败方案。新方案先说明实质差异及决策价值。C1正结果不自动成为主线。历史段落里的下一步安排须服从[当前计划](NEXT_EXPERIMENT.md)。

2026-09-29 D21有效范围32/32完成并归档。[结果](../experiments/D21_DETAIL_FREQUENCY_RESULTS_20260929.md)
显示 F2 的四块预设准确率增益和 DSM 缺失保护均失败；不要补第三种子、重调门槛、
以开发结果作为独立最终验证，或把边界诊断信号写成通过门槛。
已有数据开发实验不等待 GAMUS 来源验收。下文涉及“先等待独立来源”的旧顺序由当前下一步计划替代。

2026-09-29后续规划：未实施的D22固定Sobel门草案已被多方向方案替代。
D9B固定边缘评分失败不能因更换名称变为可靠性证据；新的学习型RGB条件残差须保留
灰度容量、原始DSM与位置打乱对照，缺失回退只记为工程保证，不称为学得的可靠性。

D11 completed 12/12 with zero queue failures by user report, but no model passed the predeclared two-seed screen. Do not rerun D11 or alter its Val2 thresholds. D12 uses new frozen decoder context and a capacity control; it is not a D11 rerun. See docs/experiments/D11_RESULTS_20260923.md.

# Completed, Closed, or Do-Not-Repeat Work

D20 修订版 GAMUS 九文件 HDF5 属性审计已于 2026-09-28 22:17:36 +08:00
完成并归档 `4cdb91f`。九文件与 Stage A SHA 相符，根节点及 `image`
数据集属性均为空；不重跑同一只读核查。地理来源与授权须由外部映射
及原始发布信息核对，见 `docs/experiments/D20_GAMUS_SAMPLE_METADATA_RESULTS_20260928.md`。

D20 修订版 GAMUS Stage A 三城 CPU 小样本审计已于 2026-09-28 18:33:49 +08:00
完成并归档。不要因入口文档的历史“待重试”段落再运行同一审计；
样本内容通过不等于来源准入。先核查上游权利、地理来源与城市级独立切分，
见 `docs/experiments/D20_GAMUS_STAGE_A_SOURCE_AUDIT_RESULTS_20260928.md`。

D18 seed17的P0/P1/P2匹配复验已全部完成，六份摘要归档并通过离线审计；
P2在两个种子分别通过原门槛，完整DSM缺失代价也已记录。保留两种子的检查点、
预测与完整服务器记录；不重跑该队列，不为了提高Val2分数追加seed或改门槛。
下一步先核对独立数据源和冻结评价协议。见
`docs/experiments/D18_REPLICATION_RESULTS_20260928.md`。

D18/D19 seed42的8项基础训练与评估已完成，零失败；原始摘要归档和离线审计通过。
P2是待seed17匹配复验的单seed候选；不重跑seed42或只给P2
补seed。C2/C3未通过冻结门槛，不为挽救它们改阈值或追加C4/C5。
见 `docs/experiments/D18_D19_RESULTS_20260928.md`。

D16/D17 completed all16 formal tasks, zero failures, with archived-summary audit passing.
A2 task-conditioned consistency and B1 RGB-feature DSM-gradient auxiliary supervision both
failed the frozen two-seed accuracy/tile screen. Do not relaunch these variants, tune their
weights on Val2, or change the screen to rescue them. Generic/shuffled/RGB controls are part
of the completed evidence. See `docs/experiments/D16_D17_RESULTS_20260927.md`.

D14 completed its frozen D13-head DSM-content intervention with eight
evaluations and zero queue failures by user-supplied server output.
DSM heads respond at the decision level; RGB controls are invariant.
Do not repeat the same Val2 intervention, infer segmentation benefit
from prediction flips, or reopen the failed D13 Stage 2 gate. See
`docs/experiments/D14_RESULTS_20260926.md`.

D13 Stage 1 completed all eight matched train/evaluation pairs with zero
queue failures by user-supplied server output and failed its prespecified
two-seed gate. Stage 2 was skipped. Do not rerun D13, run its unqualified
Stage 2, tune the risk loss on the repeatedly used Val2, or present its low
harm alone as a safety gain. See `docs/experiments/D13_RESULTS_20260925.md`.

D12 completed 14/14 with zero queue failures by user report. No core model
passed its predeclared two-seed screen; full-image confirmation was skipped.
Do not repeat the same D12 Val2 screen, alter thresholds post hoc, or train a
residual gate from it. Pooled shuffled-control attribution is provisional
until the run revision is verified against fix `d28e4af`. See
`docs/experiments/D12_RESULTS_20260924.md`.

D11 exception is a new supervised three-outcome probe with a frozen separate
protocol, not a repetition of D9B/D10M fixed scores. Fit and both calibration
roles must remain outside Val2; no hyperparameter/radius sweep follows its
results. A screening pass only leads to frozen full-resolution confirmation,
not residual-gate training. No source inventory before this runnable queue.

D10M completed: close structure_r8 and fixed local structure scoring. Do not
rerun the batch or select a different radius/budget after seeing the result.
No residual-gate training is authorized by this negative evidence.

Scheduling correction (2026-09-23): do not prolong source inventories or
retry the same proxy-blocked DFC19 URL before method exploration. D10M is a
new mechanism protocol: amplitude-preserving shifts and tie-aware harm/rescue,
not a D9B fixed-score rerun. No threshold/weight tuning on Val2. Independent
final-evaluation requirements do not prohibit this exploratory experiment.

Before launching work, compare the proposed experiment with this file and
`records/rebuild_v1_experiment_registry.json`.

Follow-up completion is user-reported; original large artifacts remain on the server.
Missing GitHub evidence is a reason to archive outputs, not rerun experiments.
B1–B4 are complete. No duplicate B4 queue or unchanged follow-up is justified.

## Closed historical directions

| Direction | Decision |
|---|---|
| Decoder-side frequency stacking | Only limited gain; no longer the main line. |
| Crop 256 | Did not provide the required advantage; stopped. |
| History30 sampling | Did not outperform Rare30; stopped. |
| Rare15 plus History15 | Did not improve the retained baseline; stopped. |
| Normal shallow detail | Final result below the retained baseline; stopped. |
| HF shallow detail | Final result below the retained baseline with class redistribution; stopped. |
| Legacy E50 reliability gate | Gate response was not a stable degradation estimator; motivation only. |
| E51 fixed-grid factor expansion | Did not support a PH-specific robustness advantage; closed. |
| Test-time GSD injection | Negative result; do not revive without a new causal design. |

## Completed REBUILD_V1 work

Do not rerun the same dataset, split, seed, schedule and configuration:

- R01 Optical-only seed42 16k;
- R02 clean Optical+DSM seed42 12k development pilot;
- R02 clean Optical+DSM seed42 16k canonical baseline;
- R03 quality-corruption seed42 16k;
- R04 modality-dropout seed42 16k;
- R01-R04 core robustness matrix;
- C-OO Optical+Optical capacity control seed42 16k;
- R05 Optical+DSM Q+D seed42 16k;
- C-OO-QD matched capacity/augmentation control seed42 16k;
- matched global robustness evaluation for R05 and C-OO-QD.
- D1-D3 local missing, local down8 and spatial-shift diagnostics for R05 and
  C-OO-QD;
- A1 no-Optical-dropout seed42 16k;
- A2 20%-DSM-dropout/no-Optical-dropout seed42 16k;
- R01, R05 and C-OO-QD seed17 16k replications and matched robustness checks.
- D4 frozen-expert complementarity analysis for seeds 42 and 17;
- D5 probability/confidence routing for seeds 42 and 17;
- D6 variable-shape missing/degraded-mask generalization for SafeMaxConfidence.
- B1 seed42 matched CE/KD/SAFE 4k continuation and robust evaluation;
- B2 seed42 R05-teacher and average-teacher controls;
- B3 seed42 paired damaged/boundary regional diagnostics for C, KD, SAFE,
  R05_KD and AVG_KD.
- B4 seed17 matched C/R05_KD/KD 4k continuation, global robustness and paired
  local damaged-region replication.
- D7 Train16 sampling and seed42/17 semantic-error audit;
- D8 seed42 4000-step C/A/S crop-sampling screen and `fix1` summary.
- D9A seed42/17 frozen-expert direct-score benefit audit across eight DSM
  conditions; do not rerun identical inference.

## Important negative or limiting findings

- R02 12k is not the formal budget; the accepted complete schedule is 16k.
- R03 is strong for mild/moderate quality degradation but does not solve
  complete DSM absence.
- R04 repairs much of the DSM-zero failure but remains below true R01.
- R05 still remains below R01 when DSM is completely absent.
- C-OO clean outperforming R02 means clean dual-stream improvement alone is
  not proof of DSM-specific value.
- Optical-zero comparisons between R05 and C-OO-QD are not semantically matched.
- A1 worsens DSM-zero fallback despite retaining 10% DSM dropout.
- A2 improves DSM-zero over R05 seed42 but remains 1.4421 pp below R01 and
  loses 1.2549 pp clean performance relative to R05 seed42.
- Increasing modality-dropout probability alone is not the active route.
- Spatial shifts produce monotonic but modest loss; do not add a registration
  module before a safer fusion path has been demonstrated.
- D4 rejects a degradation-only frozen-expert gate: local down8 prefers R05 at
  seed42 but R01 at seed17. Do not treat DSM quality as expert benefit.
- D5 SafeMaxConfidence passes the shared seed42/seed17 clean, DSM-zero and
  DSM-down8 gate; fixed probability mixtures and unconstrained confidence or
  entropy routing do not pass both seeds.
- D6 explicit/inferred-zero scores agree to four printed decimals but are not
  exactly equal in all supplied raw rows; no mask-equality test was performed.
  Known zero-fill detection is not evidence of real missing-data detection.
- D5 only supplies hard missing-region fallback to maximum-confidence routing.
  Safe probability-average/entropy controls remain untested, not ruled out.
- D4's rejected "B1 frozen-expert gate" proposal is NOT the current B1
  single-student distillation pilot; preserve this distinction in handoffs.
- B1 SAFE does not consistently improve on KD; do not repeat it unchanged.
- B2 AVG_KD does not consistently improve on KD; do not repeat it unchanged.
- B3 supports KD over R05_KD within seed42, but local missing boundaries remain
  mixed against CE.
- B4 repeats the small KD-over-R05_KD global down8/zero direction but reverses both
  paired local damaged-region directions. The documented B4 decision gate fails.
- KD17 is 0.1202 pp below C17 on global DSM-zero. Do not claim the current KD is a
  generally superior robust model.
- Do not repeat or extend the unchanged SafeMaxConfidence distillation route. A new
  run requires a materially changed reliability design and a new frozen evaluation
  source.
- D8-S improves small-Car indicators but fails the prespecified +2 pp mean
  correctness and +3 pp recall@50 joint gate. D8-A also fails. Do not run the
  conditional D8 seed17 replication or relax the gate after seeing Val2.
- Semantic prototype similarity, frequency quality, confidence and availability
  are candidate D9 evidence or controls. Do not relabel them as ground-truth
  reliability or claim them alone as the main innovation.
- D9A confidence-difference times Jensen-Shannon disagreement loses to direct
  confidence difference on benefit AUROC and AUPRC in all 16 reported
  seed-by-condition comparisons. Do not present this interaction as the new
  mechanism or retrain it unchanged on Val2.
- D9A entropy difference beats confidence difference on CE-benefit AUROC and
  AUPRC in all 16 comparisons. This is an existing baseline, not a novel gate;
  do not equate ranking with routed mIoU or a calibrated benefit probability.
- The matched safe-entropy routing audit completed with zero failures. It won
  NB mIoU over safe confidence in only 4/16 seed-condition rows, lost in 10,
  and tied in both DSM-zero rows. Do not repeat it or claim simple lower-entropy
  routing as a safety improvement.
- Original D9A `dsm_local_down8_q1` D5 routing masked degraded DSM as if it
  were absent. Its two original D5 mIoU and selected-harm rows are invalid;
  the documented two-seed `fix1` correction is complete. Do not rerun it.
- D9B's frozen unfitted input-space prototype, edge-alignment and equal-weight
  combination screen failed its decision-benefit entry gate: the full
  combination beat the stronger confidence/entropy direct control in only
  1/16 AUROC and 0/16 AUPRC rows. Do not repeat these exact scores on Val2
  or train a safety gate from them. This does not rule out different learned
  representations on an independent source.

## Legitimate reasons to rerun

A rerun requires at least one explicitly documented new variable:

- a new random seed for variance estimation;
- a new dataset;
- a new frozen split;
- a corrected implementation with a documented defect;
- a new training budget justified by convergence evidence;
- a new model component;
- a new corruption or diagnostic protocol.

A new filename or experiment ID alone is not a valid reason.

