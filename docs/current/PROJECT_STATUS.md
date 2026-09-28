# Current Project Status

**GAMUS Stage A API 分页修订待执行：**第二次服务器运行已通过隔离依赖预检，
随后在下载前遇到 Hub API `expand=true&limit=1000` 的 HTTP 400。
经复现已改用正常返回 LFS 哈希的默认 1000 项分页；没有样本下载或 GPU 训练。

**GAMUS Stage A 首次启动受缺少 `h5py` 阻塞：**报错发生在下载前；已准备只在
实验记录目录安装该 CPU 读取依赖的修订启动器。样本内容和来源准入仍待服务器重试，
没有使用 GPU 或修改训练环境。

**D20 新来源 Stage A 审计待服务器执行：**作者链接的 GAMUS 新版公开元数据包括
DC、NYC、PHL 三城 RGB／高度／标签文件；原提供的 train/val/test 混城。
已准备[9 文件 CPU 小样本审计](../protocols/D20_GAMUS_SOURCE_ACCEPTANCE_20260928.md)。
权利、内容和地理切分尚未准入；没有新 GPU 训练。DFC2019 使用/传输仍待决。

**D20 失败区域输入核查完成，2026-09-28：**17 块输入及 P0/P2 clean 预测与冻结哈希一致，
精简证据归档 `21dbb2d`。12 号块主要在标签边界外失分；14 号块 Car 假阳性增加，
总体正确像素增加而五类等权 mIoU 下降。没有发现明确文件/标签/尺寸异常。
Vaihingen seed42 门槛失败结论不变，见[核查报告](../experiments/D20_VAIHINGEN_FAILURE_INPUT_AUDIT_RESULTS_20260928.md)。

**D20 Vaihingen seed42正式开发筛选完成，2026-09-28：**三组训练、完整条件评价和分析
零执行失败；服务器结果归档`5538bf3`，本机离线计数审计通过。P2总体综合
增益+1.0261pp，但区域12/14的逐块门槛失败，故预设开发判断未通过；
seed17不自动补跑。见[完整结果](../experiments/D20_VAIHINGEN_SEED42_RESULTS_20260928.md)。

**D20 Vaihingen 训练区吞吐测量完成，2026-09-28：**16:23:08 +08:00通过并归档
`abe10e4`，12块训练区加载11.26秒，稳态每步中位0.222秒，GPU峰值0.36 GiB。
P0/P1/P2共同8,000步seed42正式同域开发队列已实现，服务器运行待验证。
见[执行协议](../protocols/D20_VAIHINGEN_SEED42_FORMAL_20260928.md)。

**D20 Vaihingen 三组一步短流程完成，2026-09-28：**16:15:54 +08:00服务器完成
P0/P1/P2训练、保存重载及单开发裁块评估；原始紧凑证据归档`8401bcd`。
这是流程验证，不能用单步 mIoU 判断方法优劣。下一步是训练区20步吞吐测量，
然后冻结正式预算。见[结果](../experiments/D20_VAIHINGEN_SMOKE_RESULTS_20260928.md)。

**D20 Vaihingen 开发来源检查完成，2026-09-28：**修正版服务器运行17/17通过
像素尺寸、DSM数值样本和完整标签颜色样本检查，原始精简记录归档`66ac041`。
地理对齐未知，既往已用区域与候选块同属一幅镶嵌图，故仅用于开发。
下一步冻结输入通道、区域切分与预处理，再实现三组匹配短流程。
见[检查记录](D20_VAIHINGEN_CONTENT_AUDIT_20260928.md)。

**D20 Stage A 服务器探测已完成，2026-09-28：** DFC19本地三元组0，官方Track-1
torrent元数据可达；GRSS/DataPort在服务器代理下403。实际数据传输与使用条件待落实。
Vaihingen已有数据，可作同域开发；部分旧场景已曝光，候选区域来自同一镶嵌图，
且光学通道是近红外/红/绿。见[Stage A 结果](D20_STAGE_A_SOURCE_ACCEPTANCE_20260928.md)。
当前D20同域正式开发队列已实现，服务器运行待验证。

**D18双种子复验完成且离线审计通过，2026-09-28：** 服务器seed17队列
14:52:05 +08:00完成三组训练/评估、配对分析和归档，失败0；原始六份
seed42/17摘要已上传。P2相对较强P0/P1的综合增益分别为+1.0603和
+0.9229 pp，两个seed各自通过全部预设门槛。完整DSM缺失时原P2
分别比P0低0.4986和0.4103 pp。下一步核对独立带标注场景来源及
类别/权限条件，然后按[D20具体计划](../protocols/D20_INDEPENDENT_SOURCE_AND_MATCHED_BASELINES_20260928.md)
先完成独立来源P0/P1/P2匹配基线：seed42初筛、通过才补seed17，最终区域留作
后续统一确认；可靠性干预另定协议。此段是D20 Stage A运行前的计划快照。
见 [结果和审计](../experiments/D18_REPLICATION_RESULTS_20260928.md)。
Val2仍为探索性，Test6冻结。以下旧状态均为历史。

**历史：D18 seed17复验就绪，2026-09-28：** P0/P1/P2匹配训练、固定seed42评价扰动、
两种子像素配对诊断、双GPU队列、约两分钟一次的ETA和精简证据归档已实现。
本地旧D18/D19 CPU检查9项通过，新复验检查3项通过；服务器CUDA短流程及正式
运行尚未观察到。按 [新执行说明](../protocols/D18_SEED17_EXECUTION_20260928.md)
启动；旧D18/D19 seed42队列已完成，不重启。Test6继续冻结。

**D18/D19最新状态，2026-09-28：** 用户服务器队列于12:13:32 +08:00结束，
8/8正式训练及评估完成、零失败；8份原始摘要、状态与decision已归档，
离线整数计数和筛选复算通过。P2在D18组内通过seed42筛选（比最强P0/P1
对照+1.0603 pp）；C2/C3失败，C4/C5按条件跳过。P2完整DSM缺失时的
原模型表现低于P0约0.50 pp，必须随候选一起报告。Val2仍为探索性，Test6冻结。
见 [结果与审计](../experiments/D18_D19_RESULTS_20260928.md)。以下较早状态为历史。

**D18/D19代码就绪，2026-09-27：** 8项seed42基础＋最多2项条件训练，自动接续评估，
已实现并通过本地9项CPU检查，CUDA/真实数据短流程待服务器。见
[执行说明](../protocols/D18_D19_EXECUTION_20260927.md)。仅等待用户启动，不写作正在运行。
最后观测的服务器完成事实仍为下述D16/D17 22:53:47。

**最新状态，2026-09-27：** 最后观测D16/D17服务器完成时间22:53:47 +08:00，
16项任务、零失败，16份原始摘要归档于e37d103且离线审计通过。A2/B1都未通过预设门槛，
当前方法变体关闭。详见 [结果报告](../experiments/D16_D17_RESULTS_20260927.md)。
下一步为匹配预训练表示/适配器对照准备；没有新队列启动证据。以下运行态为历史。

**Last observed D16/D17 server state (2026-09-26 15:29:20 +08:00):** Eight
smoke trainings failed, queue stopped before formal pilots. Shared cause from
user tracebacks: CUDA NLL2d lacks a strict deterministic implementation in the
server PyTorch. Equivalent deterministic CE is now implemented and locally
checked; CUDA regression runs in server preflight before the eight smokes.
Server replay has not yet been observed.

**D16/D17 executable queue prepared (2026-09-26), no server run observed:**
Eight configurations x seeds42/17 = sixteen4k continuation pilots. Ten local
CPU tests passed; server queue first checks both GPUs with eight train/reload/
deterministic clean-evaluation smokes, then automatically trains and evaluates.
See `docs/protocols/D16_D17_RESEARCH_PORTFOLIO_20260926.md`. Test6 prohibited.

**Last observed D15 server state (2026-09-26 14:45:11 +08:00):** All eight
evaluations completed, both workers exit0. Original summaries uploaded in
`3f95584` and offline-audited. Prespecified pooled RGB-degradation gate passed
in both seeds. Strongest reproducible target is RGB down4: both tiles/seed
comparisons improve versus RGB controls. See `docs/experiments/D15_RESULTS_20260926.md`.
No new-method queue has been launched; Val2 remains exploratory.

**Last observed D15 state (2026-09-26 05:49:46 +08:00):** Both DSM-only
trainings reached 16000 steps and completed. Both independent evaluations
failed exact clean FullGT metric reproduction; the queue stopped before
existing-expert evaluations. Deterministic evaluator settings have been
corrected, with the exact gate retained and expanded diagnostics. Server
replay is pending; the two completed models must be reused.

**Last observed D15 server state (2026-09-26 01:18:08 +08:00):** Both smoke
checks passed, but the first queue attempt ended with `worker0=1 worker1=1`
before formal training because of a shell worker variable error. The queue
script has been repaired and locally regression-tested; a server relaunch is
pending. This is an infrastructure failure, not an experimental result.

**Next queue prepared 2026-09-26, not yet observed on server:** D15 trains
matched DSM-only baselines in seeds 42/17 and measures existing R01/R05/
C-OO-QD experts under paired RGB degradation on Val2. Physical GPU0 and GPU1
are authorized for this queue, with continuation beyond one day. Read
`docs/protocols/D15_DSM_CAPABILITY_RGB_DEGRADATION_20260926.md` for the exact
launch and result checks. Historical Test6 remains frozen.

**Latest observed server state (2026-09-26 00:26:16 +08:00):** The
user-reported D14 queue completed all eight evaluations with zero failures
and `missing=[]`. DSM content intervention changes 0.0291–0.5526% of
valid Val2 pixel decisions depending on arm, seed and intervention;
matched RGB controls change zero. The D13 gain/rescue gate remains failed.
See `docs/experiments/D14_RESULTS_20260926.md`. Original D14 summaries
were transferred in commit `348dda6` and audited without discrepancy.
No further GPU queue is active in this handoff.

**Latest observed server state (2026-09-25 02:07:03 +08:00):** D13 Stage 1
finished all eight matched training/evaluation pairs with zero queue failures.
Both seeds failed the fixed family-gain and rescue-retention gates; seed 17
also failed clean-versus-R01. Stage 2 was skipped. See
`docs/experiments/D13_RESULTS_20260925.md` for the user-supplied decision
transcription and the audited original evaluation summaries transferred in
commit `8236a07`. DSM's gain beyond matched RGB capacity is small and
changes sign across seeds; the risk loss reduces both harm and rescue.
Training logs and checkpoints remain on the server. No new GPU queue is
active in this handoff; Test6 is frozen. Older pending statements below are
historical.

**Latest preparation (2026-09-24):** The D13 staged RGB-anchored DSM residual
queue is implemented for manual server launch; no D13 GPU result exists yet.
The queue includes eight mandatory matched arms and at most eight conditional
semantic/frequency/capacity arms, each at 4000 steps, with a 24-hour cap.
See `docs/protocols/D13_RGB_ANCHORED_DSM_RESIDUAL_PILOT_20260924.md`.
All D13 Val2 findings will be exploratory, and Test6 remains frozen.

**Latest (2026-09-24):** The user-reported D12 queue completed 14/14 with
zero failures and no screened candidate. Full-image work was skipped. Read
`docs/experiments/D12_RESULTS_20260924.md`; older pending text below is
historical. Original artifacts remain on the server.

- Updated: 2026-09-23
- Active branch: `rebuild-v1-protocol-20260915`
- Current line: D9A/D9B/D10M closed; D11 supervised benefit probe implemented, server execution pending
- Dataset/split: ISPRS Potsdam Train16 -> Val2 (`3_11`, `5_10`)
- Primary metric: Val2 `mIoU_fg5(noboundary)`
- Historical TEST6: prohibited for training, selection and current diagnostics
- Execution device: physical GPU 0 only (`CUDA_VISIBLE_DEVICES=0`)

Evidence provenance: core results plus compact B2/B3/B4 transcriptions are committed. The compact files were reconstructed from user-supplied validated server output; original logs, full CSV files, confusion matrices and checkpoints remain on the server and take precedence if a discrepancy is found.

## Current scheduling correction

D11 now implements the next supervised model experiment, with tile-disjoint
head fit / probability calibration / threshold calibration and cached Val2
reporting. See `docs/protocols/D11_SUPERVISED_BENEFIT_PROBE.md`. It is a
small linear three-outcome probe, not a residual gate or deep semantic model.
Train16 expert exposure and repeated Val2 use make it exploratory. No result
or benefit is claimed yet; no external-data audit is a prerequisite.

External source audits stop here. DFC19 acquisition was blocked by proxy 403.
This does not block D10M's original amplitude-preserving shift / harm-rescue
experiment on the existing R01/R05 experts. See `NEXT_EXPERIMENT.md` and
`docs/experiments/D10M_RESULTS_20260923.md`. D10M reported complete, 20/20,
zero failures; fixed structure score fails. No additional D10M queue.
This section supersedes older next-action recommendations below. Independent
confirmation remains required for final generalization claims; D10P retraining
is deferred. Learned semantic-frequency benefit models remain untested.

## D9A update (completed evidence)

The D9A safe-entropy route follow-up completed its 17-stage queue with zero
failures and verified R01/R05/safe-confidence agreement with earlier D9A.
Despite entropy's 16/16 CE-benefit ranking wins over confidence, safe entropy
improves routed NB mIoU in only 4/16 seed-condition rows, loses in 10 and
ties in both DSM-zero rows (mean paired difference -0.0089 pp). Gaussian DSM
noise remains below the R01 RGB expert for both seeds. This closes simple
lower-entropy routing as a claimed safety improvement. The source-hash-checked
stratum review found Car IoU wins in 12/16 rows, Building in 1/16, and
opposite local-down8 damaged-region directions across seeds. D9A is closed;
the next protocol is `docs/protocols/D9B_DECISION_BENEFIT_SCREEN.md`. See
`docs/experiments/D9A_ENTROPY_ROUTE_RESULTS_20260923.md`.

D9A's seed42/17 frozen-expert queue completed with zero stage failures. The
server summarizer validated source files and the deterministic DSM-zero RGB
fallback. On sampled Val2 pixels, the confidence-difference score exceeds
confidence×Jensen-Shannon disagreement on both benefit AUROC and AUPRC in all
16 seed-by-condition comparisons. A subsequent read-only review finds that
entropy difference exceeds confidence difference on both ranking metrics in
all 16 comparisons (+0.0219 AUROC and +0.0258 AUPRC on average). This is a
ranking finding, not a routed-mIoU or calibration gain. Within Car it wins
both ranking metrics in 16/16 comparisons, and within locally damaged regions
in 4/4. Existing D5 entropy-routing metric files are missing from expected
locations; the server audit found only the D5 queue directory, while seed42/17
logs report completion. The narrow frozen-expert entropy-route mIoU/harm
audit is complete and reported above. The D9A local-down8 D5 routing result
was invalid because the original code treated degraded DSM as
known absence; the two-seed fix completed with zero failures. Corrected D5 NB
mIoU is 86.8285%/86.2557%, with unchanged benefit-ranking CSVs. Under
normalized DSM Gaussian noise sigma 0.10, D5 is below R01 by 0.1814/0.3190
pp NB mIoU for seeds 42/17, despite
its exact R01 fallback when DSM is completely absent. This is a negative
result for the tested direct disagreement interaction, not the full D9
semantic/frequency hypothesis. See `docs/experiments/D9A_RESULTS_20260923.md`.

## D7/D8 update

D7 completed. Train16 has a 15.9175x foreground pixel-frequency ratio;
small Car is harder than medium/large Car, but Car is not the lowest-IoU class.
R05 helps Building while it can harm Car. D8 then compared matched R01 seed42
4000-step random (C), any-Car-centred (A) and small-Car-centred (S) crops.
The `fix1` queue completed on 2026-09-22 17:59:55 +08:00 with zero failures,
and all run summaries report `test6_loaded=false`.

S versus C improves small-Car mean correctness by 1.8579 pp, recall@50 by
1.2987 pp and Car IoU by 0.9159 pp. It fails the predeclared +2 pp mean
correctness and +3 pp recall requirements. A reduces small-Car mean correctness
by 1.0097 pp. D8's joint gate failed for both candidates; no seed17 arm is
authorized by this protocol. See `docs/experiments/D8_RESULTS_20260922.md`.

The next question is whether observable semantic, frequency and expert-disagreement
evidence predicts the label-defined marginal DSM benefit over R01. D9 remains
diagnostic until an independent fitting/calibration/evaluation source and a
fitted-combination protocol are frozen. See
`docs/protocols/D9_DSM_BENEFIT_DIAGNOSTIC.md`.

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

D7 and D8 are closed diagnostics. D9A is complete but cannot pass the full D9
gate, because semantic/frequency combinations and independent evaluation are
absent. Do not turn these Val2 findings into a final paper claim. B1–B4 remain
closed. The proposed paper direction is benefit-aware suppression of negative
transfer from DSM, subject to further D9 evidence.

D9B's unfitted decision-benefit screen is complete by user-reported server
summary (zero queue failures, 16 seed-condition rows). The handcrafted
semantic+frequency+expert score beat the best direct confidence/entropy
control in only 1/16 flip-benefit AUROC and 0/16 AUPRC comparisons. Its
cross-seed entry gate failed, so no learned safety gate is authorized from
these features. See `docs/experiments/D9B_RESULTS_20260923.md`. The result
is exploratory Val2 evidence; per-stratum source files remain on the server
and an independent labelled source has not yet been frozen.
