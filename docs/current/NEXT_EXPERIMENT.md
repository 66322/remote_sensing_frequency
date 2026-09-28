# Next research decision after D18/D19 (2026-09-28)

下一轮具体规划见 [D18匹配seed17复验与配对诊断](../protocols/D18_MATCHED_SEED17_REPLICATION_PLAN_20260928.md)：
3项新训练，复用seed42；GPU0/1并行，预计2–3小时含检查和诊断。
模型初始化/训练采样改为seed17，评价扰动固定，并增加相对同seed P0的
像素配对纠错/改错分析。当前仅规划，未实现或启动。

**当前决定：**D18/D19 seed42 基础队列已于 2026-09-28 12:13:32 +08:00
按用户提供的服务器日志完成8/8、失败0。P2通过预设单seed筛选；C2/C3失败，
C4/C5按条件跳过。见 [结果记录](../experiments/D18_D19_RESULTS_20260928.md)。

8份评估原始摘要、完整队列状态、条件筛选和最终decision已归档到GitHub，
离线重算审计通过。下一批应为 P0/P1/P2 三组匹配seed17复验：冻结DINO权重、
模型结构、训练预算、采样/退化分布和全部评价条件，仅改变种子；该复验代码
及队列尚未实现或启动。预先报告完整DSM缺失的原模型指标：seed42 P2为
81.6224%、P0为82.1209%，P2低0.4986 pp。显式回退到旧R01的输出必须
单列，不能算作P2自身学到的缺失鲁棒性。
不能只补 P2 或把与旧R05的横向绝对分数当作同预算机制比较。Val2反复使用，
即使跨种子重复也只是开发探索；独立场景确认仍需另定来源。Test6冻结。

以下较早的“等待启动”段落为历史记录，不再执行。

**最新可执行安排，2026-09-27：** D18/D19已实现，等待用户启动。
见 [执行说明与一条启动流程](../protocols/D18_D19_EXECUTION_20260927.md)：8项seed42基础任务，
结构通过后最多2项条件任务，自动训练/重载/评估/汇总，GPU0/1共享就绪任务。
D18选择冻结DINOv2 ViT-S/14，后台独立环境准备，不阻塞独立D19。
本地9项CPU测试通过、2项CUDA待服务器，尚无服务器新任务启动或结果证据。
以下“只有计划、尚未实现”内容为历史，已由执行说明替代。

**最新夜间计划，2026-09-27：** 用户要求多方案单seed初筛并自动接续评估。
见 [D18/D19夜间计划](../protocols/D18_D19_NIGHT_SCREEN_PLAN_20260927.md)：
预训练适配器3项＋结构化干预融合5项基础任务，结构有信号后最多再触发2项。
全部seed42，不自动追加seed17；各项训练后完成重载、全图评估和固定新扰动诊断。
仅计划已写，模型/权重选型、可执行配置与队列尚未实现；下一步是实现完整闭环。
本计划替代此前默认三配置双seed的资源安排，D16/D17关闭结论不变。

**当前决定，2026-09-27：** D16/D17在22:53:47 +08:00完成，16项任务无失败。
16份归档原始摘要审计通过，A2/B1均未通过预设双seed筛选。见
[结果报告](../experiments/D16_D17_RESULTS_20260927.md)。关闭本批变体，不重启或扫损失权重。
优先准备同一预训练起点与预算的RGB、RGB+灰度辅助、RGB+DSM辅助适配器对照，
先完成权重/输入/环境与全训练评估链验证；尚未实现或排新队列。
点监督实例分割做数据可行性备选，ISFuse不自动追加。下文等待/启动指令为历史。

**当前安排：等待本轮完成，2026-09-27 计划复盘。** 用户要求将 ISFuse 迁移
与 D16/D17 结果统一讨论，暂不追加运行。见
[`次日复盘议程`](../protocols/POST_D16_D17_REVIEW_20260927.md)。若明天未完成，
先整理进度，继续当前队列，不将不完整结果判为方法失败。
新增 [2025–2026分割与交叉方向筛选](../protocols/SEGMENTATION_CROSSOVER_2025_2026_REVIEW_20260926.md)，
供复盘时选一条主路线和一条备选，涵盖几何、点监督实例、按需计算、跨域、开放词汇与遮挡补全。
这些是未实施建议，须先过结果/数据/实现门槛，不是新服务器队列。下述修复启动说明为历史。

**Immediate action:** Pull the strict-CE compatibility repair and relaunch
`scripts/run_rebuild_v1_d16_d17_queue.sh`. All eight smokes failed on legacy
CUDA NLL2d before any optimizer step; sixteen formal pilots have not started.
Strict deterministic mode is retained. New loss/gradient equivalence and CUDA
regression checks precede the server smoke gate. Keep failed logs; no deletion.

**Post-D15 plan corrected, 2026-09-26:** Keep RGB-DSM complementary/reliable
segmentation as the research problem. Down4 is a stress condition, not a pivot
to SR. The proposed next batch is eight configurations x seeds42/17 = sixteen
4000-step continuation pilots: paired-intervention task consistency with
generic/shuffled/RGB-capacity controls, plus aligned-versus-shuffled geometry
supervision. See `docs/protocols/D16_D17_RESEARCH_PORTFOLIO_20260926.md` for the
matrix, stop rules, two-GPU ready-job scheduling and reserved pretrained-adapter
direction. Executable config and train/eval/shared GPU0/1 queue are implemented;
ten local CPU tests passed. Server CUDA smoke and launch not yet observed.
Launch `scripts/run_rebuild_v1_d16_d17_queue.sh` using the protocol commands;
eight end-to-end smoke jobs gate sixteen4k pilots and automatic evaluation.
D15 is complete;
do not rerun it. Earlier queue/repair instructions below are historical.

**D15 relaunch pending after queue repair:** User-reported 01:18:08 +08:00
status shows both smokes passed but both workers exited before formal training.
Pull the repaired queue script and rerun the same launch command in the D15
protocol. Existing smoke summaries will be reused; no D15 research result
exists yet.

**D15 queued for user launch; server execution not yet observed.** The next exploratory batch is the two-GPU D15 DSM-only capability and RGB degradation evaluation in [`D15_DSM_CAPABILITY_RGB_DEGRADATION_20260926.md`](../protocols/D15_DSM_CAPABILITY_RGB_DEGRADATION_20260926.md). It trains two matched 16k DSM-only seeds, evaluates R01/R05/C-OO-QD under paired RGB degradation on both seeds, then summarizes a prespecified exploratory gate. The user's new authorization allows physical GPU0 and GPU1 and continuation beyond one day. After pulling this branch, run the launch command in that protocol. D15 results will choose the *next* method protocol; no untested recovery architecture or harm/rescue training is auto-launched.

**Current decision after D14, 2026-09-26:** D14 completed 8/8 paired
inference evaluations with no queue failures. It detects DSM
decision-level sensitivity but no stable mIoU benefit; D13's failed
gain/rescue gate is unchanged. Read
`docs/experiments/D14_RESULTS_20260926.md`. Do not relaunch D14,
run D13 Stage 2, or tune its risk penalty on Val2. The eight original
D14 summaries were transferred in commit `348dda6` and the per-tile/class
audit is complete. The subsequent research decision should focus on a
new method target and an independent labelled scene source before any
confirmatory claim. No GPU queue is currently specified. The older D14
launch instructions below are historical.

**Current decision, 2026-09-25:** D13 Stage 1 completed but failed its
prespecified two-seed gate; the queue correctly skipped Stage 2. No D13
relaunch or threshold adjustment. The eight full-image Val2 summaries were
transferred in commit `8236a07` and audited. Matched comparisons show a
small DSM-specific increment that reverses across seeds and a risk loss that
suppresses both harm and rescue. See
`docs/experiments/D13_RESULTS_20260925.md`. The next bounded question is
whether the trained DSM heads respond to DSM content when the availability
mask is held fixed. If pursued, predeclare a short inference-only
counterfactual protocol with matched RGB heads as a negative control and
paired full-image condition/class/tile metrics. Do not infer modality use
from the current near-invariant corruption results alone. A new training
objective requires its own protocol and an independent evaluation source
for confirmatory claims. Test6 remains frozen. All D13 launch instructions
below are historical.

**2026-09-24 runnable exploratory plan:** After reviewing D9-D12, the next concrete
method question is a staged RGB-anchored DSM residual training pilot, specified
in `docs/protocols/D13_RGB_ANCHORED_DSM_RESIDUAL_PILOT_20260924.md`.
Stage 1 compares matched RGB-capacity, DSM-CE, RGB-risk, and DSM-risk arms in
both seeds (eight runs); Stage 2 adds up to eight semantic/frequency/capacity
ablations only on a both-seed pass. The requested unattended plan has a
24-hour cap, fixed 4000-step runs, frozen numerical continuation margins,
automatic diagnostics on failure, and final summaries. The D13 queue is now
implemented; local CPU numerics and syntax checks passed, while server smoke
and GPU training are pending. It is a
new training mechanism, distinct from the failed D12 frozen-expert selector.
Potsdam Val2 can give exploratory development evidence only; an independent
scene source is still required for final confirmation. Do not use Test6.

After pulling this branch on the server, launch once from
`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro` in the `remote_sensing`
environment:

```bash
git pull --ff-only origin rebuild-v1-protocol-20260915
mkdir -p records/rebuild_v1_d13_residual_queue_20260924
nohup bash scripts/run_rebuild_v1_d13_residual_queue.sh > records/rebuild_v1_d13_residual_queue_20260924/launcher.log 2>&1 &
```

The queue performs its own GPU-boundary, numeric, training-smoke and
Train16-only evaluation-smoke checks before formal work. Later inspect
`records/rebuild_v1_d13_residual_queue_20260924/status.tsv`,
`D13_STAGE1_SUMMARY.log`, `D13_FINAL_SUMMARY.log` in that directory, and
`records/rebuild_v1_d13_residual_20260924/final_decision.json`. No manual
intermediate decision is required. The executable commands below under the
historical D12 heading are obsolete.

D12 completed 14/14 heads with zero queue failures and **no candidate** under
the prespecified two-seed gain/harm screen. Complete-image confirmation was
correctly skipped. The exact server-output transcription and interpretation
are in `docs/experiments/D12_RESULTS_20260924.md`. Do not relaunch D12 or
relax its Val2 thresholds after seeing the result.

The historical next step was a bounded decision memo using D9–D12 evidence: decide whether
a benefit-aware selector warrants a new experimental design. A new fitted
method needs a genuinely changed mechanism or supervision target and a frozen,
spatially independent labelled evaluation source. The repeatedly inspected
Val2 cannot serve as confirmation. Keep the question of DSM's marginal
decision value over RGB, but do not claim that this semantic/frequency head
solves it. Do not train a residual gate from the failed D12 selector, run Test6
evaluation, or launch another
same-source parameter sweep. The DFC19 proxy failure is not a reason for
another prolonged audit now. The launch instructions below are historical.

# Historical D12 launch plan (completed)

D11 finished on the server at 2026-09-23 18:51:37 +08:00 according to the user's pasted queue and summary. All 12 models completed with zero queue failures; none passed the predeclared two-seed screen. The result is transcribed at `docs/experiments/D11_RESULTS_20260923.md`.

D12 implements the next approved exploratory batch: five core predictor comparisons plus two spatial-correspondence controls for each of seeds 42 and 17. It extracts frozen R01/R05 decoder measurements, reuses D11 development and D10M evaluation probability samples, trains small three-outcome heads, and conditionally verifies at most two passing models on complete Val2 images. See `docs/protocols/D12_NIGHT_SEMANTIC_FREQUENCY_20260923.md`.

The code has local CPU numeric tests. Server smoke and execution are pending. Physical GPU0 only; all runtime artifacts under `/home/jovyan/zzx`; Test6 frozen. The script refuses to overwrite existing records and caps wall time at eight hours. The user starts the queue after pulling this branch on the server.

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
conda activate remote_sensing
git pull --ff-only origin rebuild-v1-protocol-20260915
mkdir -p records/rebuild_v1_d12_night_queue_20260923
nohup bash scripts/run_rebuild_v1_d12_night_queue.sh > records/rebuild_v1_d12_night_queue_20260923/launcher.log 2>&1 &
```

Tomorrow, inspect `status.tsv`, `D12_SUMMARY.log`, and `D12_FULL_SUMMARY.log` in the queue directory. `records/rebuild_v1_d12_night_20260923/decision.json` identifies screened candidates and `full_summary.json` records complete-image job coverage. A queue FINISHED line alone does not establish that all stages passed.
