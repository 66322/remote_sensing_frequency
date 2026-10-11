# 2026-10-11：双卡执行包就绪，待服务器登记

[操作说明](../../protocols/POST_T_PAIRED_V2_EXECUTION_20261011.md)、[实现检查](../../../records/post_t_paired_v2_implementation_20261011/verification.json)。6新训练/72000步＋2批48 case，GPU0/1共享队列；用户release任一卡，保存退出后断点与待办在另一卡排队，显式rejoin前停用原卡。无全队24h截止。当前READY_NOT_REGISTERED_GPU_RUNTIME_UNVERIFIED，无新目录/PID/真实GPU结果回报；本地CPU检查不是正式实验。

原26项不重复运行。最新用户双卡授权覆盖下方历史只GPU0限制，科学v2不变；最后服务器查询仍13:48:26+08:00。以下为历史条目。

---

# 2026-10-11：v2后续实验设计，尚未登记

[研究排期](../../protocols/POST_T_RESEARCH_SEQUENCE_20261011.md)、[配对细则v2](../../protocols/POST_T_PAIRED_ADAPTATION_BUDGET_20261011.md)、[设计清单](../../../records/post_t_research_plan_v2_20261011/design.json)。六核心训练F/H/R×8k/16k共72000更新；48个0训练DSM内容诊断case；X8/X16转为不可自动派发储备。DESIGN_FROZEN_NOT_IMPLEMENTED_NOT_REGISTERED，没有新实验结果/服务器登记。核心顺序H8/F8/R8/R16/H16/F16，两批内容诊断分别置于前后。

旧Post-T原件验收不变；最后服务器查询13:48:26+08:00，26项完整退出。v1八项提案已在新结果出现前修订；下方提及八项/96000的旧段落均为历史方案，当前以v2为准。H纳入net.rgb与decoder[:-1]，R再开启末4块；容量和内容敏感性边界明确，不能自动推成论文贡献。

---

# 2026-10-11：Post-T 26项原件验收与下一轮协议

本轮Post-T原件57ef5ad9e5238f69f94c5d8ede00023a20499144已接收并离线验收，Verification Status: ANALYZED。最后服务器查询2026-10-11T13:48:26.474610+08:00；queue完成观测13:42:45.195415，CPU完成、26/26 COMPLETE、查询时controller及全部worker LIVE=False，仅GPU0、0新优化器更新。此为最后服务器观测，上传与助手离线分析不构成实时查询。

核验全部634个Git blob（633载荷＋manifest）、632份源字节/无损解码SHA、50860矩阵/11424 joint边际、296 case/888预测索引与1184 transition计数关系。M333_context全部16 case的候选预测SHA和计数复现R0，RGB_U=85.001650%。155份上传代码/文档按执行manifest核验；3份继承历史plan JSON不在本轮上传器范围，名单详见审计。CPU11项原日志OK已接收。权重/预测/影像本体留服务器，未独立重hash或GPU重跑。

固定RGB_U比较：只换解码器+0.504953pp，换RGB专家包+2.901426pp，换DSM专家包+0.005618pp；同S1-3解码器下换两包+2.521564pp，两tile均正；M333上下文对屏蔽+3.421234pp。RGB包来源在context下四对+2.519—2.901pp，masked下几乎无效，有强交互。包包含编码器与专家解码头，不能归因为纯编码尾部，也不能从DSM交换小效应否定DSM内容。

固定T1/T7后4000步RGB_U分别+0.334083/+0.321695pp，两tile正，两预定规划信号独立复算True。它们仅支持新配对研究，不证明延长旧T7必成。完整T原gate仍T7/U/E=False，旧失败不救援。0/8000计数与4000 validation绑定复用此前已验完整T审计，新4000 U原计数独立复算。

[结果](../POST_T_MECHANISM_RESULTS_20261011.md)、[四机制×两预算协议](../../protocols/POST_T_PAIRED_ADAPTATION_BUDGET_20261011.md)、[审计](../../../records/post_t_mechanism_offline_audit_20261011/audit.json)。

研究阶段：可行性探索与机制定位；主线仍RGB–DSM双向条件互补与退化/缺失分割，任务驱动恢复为旁支。实验已验证的机制线索限已知RGB局部缺失、重复Val2/seed42；不声称双向、未知可靠性或独立泛化。

本次按用户要求制定下一轮真正配对训练协议，属于重写版建议：F普通私有解码、H只适应RGB专家pre-classifier解码头、R加RGB末4编码块、X与R等参数空间打乱控制，各新8000/16000，共8项/96000更新；固定候选R16。所有初值S1-0，同预算数据/优化器/日程配对，含保护/R0/最坏tile/六E底线。8k/16k为预算×日程联合比较，不是纯次数因果。协议PLANNED_NOT_IMPLEMENTED_NOT_REGISTERED，没有新队列、PID或训练启动。

未采纳只延长旧T7、解码器迁移初值救gate、新seed、GPU1、DSM镜像族或恢复旁支扩张；没有改选M303/T5。下一不确定性是专家解码头还是末端编码适应能形成同预算增量、是否超过等容量/空间控制以及能否满足保护/R0底线。

以下为历史记录；待上传/旧进度条目不代表当前状态。

---

# 2026-10-11 13:48：机制诊断26/26完成，原件待上传

最后服务器查询（用户粘贴终端回报）：QUERY_OBSERVED=2026-10-11T13:48:26.474610+08:00；queue LAST_OBSERVED=2026-10-11T13:42:45.195415+08:00，MECHANISM_COMPLETE_AWAITING_REVIEW。CPU完成，M16＋L10全部26项COMPLETE；查询时controller PID3626108及全部worker LIVE=False，仅GPU0，NEW_OPTIMIZER_UPDATES=0。nohup完整派发/完成并NO_FURTHER_DISPATCH，未见本次故障回报。这是最后观测，不代表新的实时查询。

服务器DIAGNOSTIC_SCREEN回报matched_budget_study_supported=True、representation_followup_signal=True；next_training_launched=False、automatic_retry=False。此为未独立验收的汇总回报，未收到本轮精度、原计数、checkpoint绑定或R0同源端点原件；不能判新方法有效或把信号当作双向贡献。来源：[完成回报](../../../records/research_post_t_mechanism_20261011T094823_3625851/user_reported_completion_20261011T134826.json)。

执行提交cd958925cb5d4292dd15802830e97493c9c67033保持，目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_t_mechanism_20261011T094823_3625851。M333_context完成观测13:04:28；L十项worker实测206.411—210.024秒/项，最后L_T9完成观测13:42:23。旧剩余估时已失效。

立即下一步：在用户服务器终端用原目录code/scripts/upload_post_t_mechanism_records.py --root ROOT --directory DIR显式上传轻量原件，无需再次登记或启动。仅上传轻量JSON/计数/配置/代码/日志及服务器大文件索引，权重和预测数组保留原目录；用户返回上传提交号后助手从GitHub回读。

先核验清单/无损解码SHA、26项完成与执行绑定、M333_context对全部16个R0 case逐像素同源端点、int64 6×6计数及tile→pooled；再复算固定模块配对与全部因素配对、保护底线、0→4000→8000 RGB_U/DSM_U轨迹和4000 checkpoint绑定。未校准交换负结果不能证明信息缺失。

原件通过后，依据专家包信号与T1/T7固定后段信号制定真正的配对训练协议：明确待训练参数、同预算普通控制、冻结/简单解冻/容量控制、主指标、保护与停止门槛及学习率日程。下一轮尚未定型、未登记、未启动；不直接续跑已衰减到零的8000步日程救旧gate。

服务器由用户执行、无SSH；仅GPU0，不访问Test6/held4/final，不自动重跑失败配方、加seed或GPU1。所有记录/执行快照/归档在/home/jovyan/zzx对应目录。重要结论与交接继续写同一GitHub分支并回读。

---

以下为历史阶段记录，当前状态以START_HERE为准。

# 2026-10-11 12:55：15项M完成，最后M运行，L10待运行

最后服务器只读查询（用户终端粘贴，未接收本轮指标原件）：QUERY_OBSERVED=2026-10-11T12:55:27.487901+08:00，queue LAST_OBSERVED=2026-10-11T12:55:15.361980+08:00，RUNNING_M333_context；controller PID3626108 LIVE=True，CPU=COMPLETE，仅GPU0。15/26整项COMPLETE、1项RUNNING、10项PENDING；前15个M已完成并退出，M333_context PID3718262 LIVE=True，phase=inference，tile=3_11，condition=rgb_lines64w8__aux_down4，windows=529/529，progress观测12:55:24.648101，elapsed=158.271144秒，optimizer_updates=0。单tile/条件窗口完成不等于整项完成。L_T0—L_T9尚未启动。这是最后观测，不代表实时状态。

前序已安全交接，原执行cd958925cb5d4292dd15802830e97493c9c67033与原目录research_post_t_mechanism_20261011T094823_3625851保持。所贴nohup日志确认依序完成15个M并启动M333_context，未见本次故障回报；没有精度、R0同源端点或训练轨迹原件，不能判机制成立。新增训练0。回报见[进度摘录](../../../records/research_post_t_mechanism_20261011T094823_3625851/user_reported_progress_20261011T125527.json)。

已完成15个M的worker耗时704.836—760.205秒（约11.7—12.7分钟），替代未校准的2—4h估时。12:55时最后M约余9—10分钟；L每项只有4个tile单元，但加载/散列与汇总耗时未测，整队剩余仍须首个L实测校准。不得按条件数线性缩放承诺ETA。

继续原队列；技术全部完成后显式上传轻量原件，核验R0端点/计数/绑定，再分析模块与0→4000→8000轨迹。主线、旧T gate和未定型训练状态不变。以下09:51及更早条目为历史观测。

---

# 2026-10-11 09:51：机制诊断首项GPU0推理已确认

最后服务器只读查询（用户终端）：QUERY_OBSERVED=2026-10-11T09:51:04.266613+08:00，queue LAST_OBSERVED=2026-10-11T09:50:54.789468+08:00，RUNNING_M000_masked；controller PID3626108 LIVE=True，CPU=COMPLETE，仅GPU0。首项M000_masked PID3626555 LIVE=True，phase=inference，tile=3_11，condition=dsm_U，windows=529/529，progress观测09:50:47.640628，elapsed=81.824804秒，optimizer_updates=0。

前序已安全交接：READY、controller_live=False、workers_live=False，checked_at=2026-10-11T09:48:31.724509+08:00；原T最后观测08:45:44.211597。当前0/26整项完成、1项运行、25项PENDING；529/529仅为单tile单条件窗口进度，不代表整个M项或队列完成。暂无新精度/R0端点/机制结论，也无本次故障回报。

继续现有nohup队列，使用原status按需只读观察，不重复enqueue。顺序M16→L10，GPU0单worker、0训练更新；接手后2—4h仍为规划估时，首个完整M后校准。失败保留worker/目录后诊断，不自动重试、追加seed或GPU1；完成后上传轻量原件再分析。

---

# 2026-10-11 09:48：机制诊断登记成功，进度待查询

最新服务器登记回报（用户终端，2026-10-11）：MECHANISM_QUEUE_REGISTERED，目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_t_mechanism_20261011T094823_3625851，controller PID3626108，GPU=0 ONLY，DIAGNOSTIC_JOBS=26，NEW_STEPS=0；日志nohup_20261011T094831668881.log。目录09:48:23、日志09:48:31.668881为命名时间标记，不是queue observed_at。当前REGISTERED_PROGRESS_NOT_YET_QUERIED，尚无controller/worker存活、CPU准备或CUDA首项进度回报。

前序检查回报：LAST_OBSERVED=2026-10-11T08:45:44.211597+08:00，TRANSFER_COMPLETE_AWAITING_REVIEW，READY；它确认登记时前序已满足交接检查，不代表新诊断已有完成结果。执行提交cd958925cb5d4292dd15802830e97493c9c67033。登记前CPU检查成功返回由入口链推断，尚未单收服务器cpu_checks.log。

下一步只读新目录code/scripts/status_post_t_mechanism.py以及nohup/preparation日志，确认CPU准备、controller存活及首个M任务；不要重复enqueue或重启T。26项自动串行、仅GPU0、0训练更新，预计接手后2—4h为粗范围，尚待首项校准。失败时保留目录/worker并诊断，不自动重试。结束上传轻量原件，再定后续训练。

---

# 2026-10-11完整T验收与26项诊断采用

最后服务器观测2026-10-11T08:45:44.211597+08:00，TRANSFER_COMPLETE_AWAITING_REVIEW；T0—T9十组全部COMPLETE/8000，CPU完成。快照2026-10-11T09:32:36.322168+08:00，原件379f301f255b9d2348cf11cad79e1374fedd1e7b。此为带时间证据，不是实时服务器查询。

整轮T7=False、U=False、E=False按原门槛保持：T7 RGB_U=83.876407%，相对T1 +0.019790pp、T9随机初始化 +0.059297pp（均逐tile异号），相对T6 +1.453117pp；相对基础+2.863806pp，但比R0=85.001650%低1.125243pp。所有五个上下文匹配对+1.432～+1.521pp且两tile均正；解码器初始化的额外收益未获支持。

采用已实现的POST_T_MECHANISM作为下一阶段：16个权重模块包×上下文组合＋10个已有4000步U推理，共26项/296个模型×条件×tile单元/0优化器更新。仅GPU0；READY_NOT_REGISTERED，尚无新服务器登记/PID/运行回报。用户授权自动接续保持，注册时检查原队列完成、进程退出及锁释放，再自动串行执行；不重启T。

[整轮结果](../POST_T_FULL_RESULTS_20261011.md)、[下一阶段协议](../../protocols/POST_T_MECHANISM_GPU0_20261010.md)。此前全轮待上传/候选未定为历史条目。

---

# 最新更新：2026-10-10 T后26项机制诊断就绪（未登记）

2026-10-11用户补充：原T实验可能已全部完成，要求结合整轮结果再规划。GitHub回查仍为bce81d59f2fd188a5e500354c4c93be8b7771937，仅T0—T4原件；T5—T9及最终screen未上传，不能确认新完成状态。以下26项为已实现的候选后继，尚未登记；先接收完整T记录，再决定是否原样采用，不把部分证据规划当作全轮结论。

新后继POST_T_MECHANISM：READY_NOT_REGISTERED。26项固定推理（16模块包组合＋10个已有4000步checkpoint），296个模型×条件×tile单元，新增优化器更新0，仅GPU0。代码已实现、11项CPU检查通过；135个继承Python文件与原执行manifest核对一致，真实GPU/权重验收留服务器。尚无新目录/PID/执行回报。

最后服务器证据仍为2026-10-10T21:28:41.841837+08:00，原T队列RUNNING_T5；T0—T4已收原件，T5运行、T6—T9待运行，固定T7未收。这是历史观测，不是实时查询。旧Post-S1最后观测2026-10-10T08:13:57.270242+08:00，已完整结束。

[冻结协议](../../protocols/POST_T_MECHANISM_GPU0_20261010.md)：16个模块包×上下文组合、10个4000步U评价；用户授权接续，登记后自动等T技术完成与GPU0释放。无新训练，R0端点精确核验；原T7 gate不改，新的方法训练需诊断后定型。

---

# REBUILD_V1 Experiment Index

## 2026-10-10 旧Post-S1完整与T0—T4部分验收

|阶段|最后观测与状态|结论|证据|
|---|---|---|---|
|Post-S1十P+D0/D1/E|10月10日08:13:57，完成待复核|上下文四对正收益；P7总门槛失败、E通过、Q跳过；P3仍低于R0|[完整报告](../POST_S1_FULL_TRANSFER_PARTIAL_RESULTS_20261010.md)|
|GPU0后继T0—T9|10月10日21:28:41，T0—T4完成/T5运行/T6—T9待运行|两对上下文收益复现；T3≈T1，迁移收益未成立；T7未收到，不判整轮|[协议](../../protocols/POST_S1_TRANSFER_GPU0_20261009.md)、[审计](../../../records/post_s1_result_analysis_20261010/audit.json)|

本索引不决定论文主线。路线角色见[研究决定](../../current/RESEARCH_DECISION.md)。以下为历史阶段记录。

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


## 2026-10-05 12:15 N2运行与估时

最后服务器观测（用户终端回传）：2026-10-05T12:15:02.465274+08:00，QUEUE=RUNNING_N2，修复控制器PID3467202 LIVE=True。GPU0 N2-0原worker PID3457210 LIVE=True，训练已达8000/8000，正在fixed8000评价；progress观测12:14:49.587910，tile=3_11、condition=geom_warp8+rgb_down4、windows529/529，仅当前条件/tile窗口完成，不是作业COMPLETE。GPU1 N2-1 PID3467394 LIVE=True，training7800/8000，progress观测12:14:52.484868，剩200步约4.4分钟（不含之后验证/评价）。N2-2—5仍PENDING，当前完成标记0/6；没有新中断回报或精度结果。两卡当前训练每步约1.309/1.316秒，后续各两项纯训练约5.82/5.85小时；从12:15开始不计评价的训练完成下界约18:10。计入当前及后续checkpoint选模、fixed8000/selected条件评价与汇总，整队暂估2026-10-05北京时间20:00—22:00（规划范围、非已测评价耗时或保证）；首轮COMPLETE与评价耗时回报后再校准。科学86b6、控制器修复9b196a2、N2-0原worker接管保留；继续现有队列，按需只读查询，不重启。

[原始状态转录与估时假设](../../../records/research_post_ab_followup_n2_20261005T085829_3456726/user_reported_running_20261005T121502.json)。估时只覆盖当前N2六组，不包括未激活E0/E1/E2及N3/N4/N5；后续新算子/选模checkpoint复用条件可能改变耗时。

## 2026-10-05：E0/E1/E2后继执行包已就绪

用户“那开始吧”授权实施；[执行协议](../../protocols/POST_N2_DIAGNOSTICS_EXECUTION_20261005.md)和[CPU就绪记录](../../../records/research_post_n2_diagnostics_plan_20261005/validation.json)。代码已实现，16项CPU检查/10文件语法通过；2026-10-05本次回报已确认诊断目录research_post_n2_diagnostics_20261005T131434_3591073登记、返回PID3591245；控制器LIVE/等待状态未查询，不能写为运行成功。原N2最后简报13:14:31.018288+08:00为RUNNING_N2/PID3467202 LIVE=True，作业完成数未报告。N2完成并释放后复核原件、E0读已有预测，E1/E2共60次新tile推理/0训练。GPU0/1、nohup、zzx独立目录；不读T预留规则/Test6、不自动训练N5/N3/N4、不重启旧队列。

本次[登记观测](../../../records/research_post_n2_diagnostics_20261005T131434_3591073/registration_observation.json)来源为用户粘贴终端输出，不替代原日志/运行原件验收；下一步只读查询，不重复启动。

2026-10-05T13:20:35.646566+08:00用户只读回报：诊断后继WAITING_N2、PID3591245 LIVE=True，E0/MASKS及五worker全部PENDING，新增训练0；nohup持续WAITING_N2 RUNNING_N2。等待正常，不启动/修复，不称新推理已运行。原N2详细完成数未提供，原控制器独立存活最后观测13:14:31。见[等待观测](../../../records/research_post_n2_diagnostics_20261005T131434_3591073/waiting_observation_20261005T132035.json)。

## 2026-10-06收到本轮完成回报（完成时刻2026-10-05 23:27）

最后服务器观测（用户2026-10-06回传）：queue_status观测时间2026-10-05T23:27:15.831648+08:00，诊断后继DIAGNOSTICS_COMPLETE_AWAITING_REVIEW，PID3591245 LIVE=False；E0/MASKS COMPLETE，E1_A0/B1及E2_N1-2/N2-0/N2-3五项全部COMPLETE，worker均LIVE=False，新增optimizer更新0。nohup已记录READY N2_COMPLETE_AWAITING_STAGE_PROTOCOL和完整派发/完成序列，无本次故障回报。POST_N2_DIAGNOSTICS_SCREEN True True对应N5问题触发=True、N3问题触发=True，不是两种训练方法有效。N2原科学gate、诊断数值/原件尚待上传回读；不可称已独立验收或确认贡献。

E0读取已有预测完成，掩码准备完成；E1两worker分别436.28/441.19秒，E2三worker430.03/431.00/427.27秒，五任务实测均约7.1–7.4分钟。E1/E2三个派发波次从约23:05至23:27完成（起始按progress elapsed推算），新增60次tile推理/0训练。CPU E0最后进度23:05:12.250016，缺少CPU开始记录，不能据此推算E0总时长或原N2完成时间。

N2/E0/E1/E2原轻量summary/矩阵仍待[上传](../../current/NEXT_EXPERIMENT.md)，此条只有用户终端完成状态与日志，不是独立原件验收。两个问题门槛不代表方法贡献；保持原N2科学gate，未启新N5/N3/N4训练。N2上传器补收controller-only修复轻量原件，不修改科学快照。

## 2026-10-06：N2与E0/E1/E2原件已接收/独立验收

最后服务器记录以已上传原件为准：N2 queue观测2026-10-05T22:11:34.641183+08:00，N2_COMPLETE_AWAITING_STAGE_PROTOCOL、六组COMPLETE；诊断queue观测23:27:15.831648，DIAGNOSTICS_COMPLETE_AWAITING_REVIEW、E0/MASKS和五worker COMPLETE、新增训练0。2026-10-06已收到N2 a33872c和诊断7c47c49两次原件上传；本次助手只做GitHub回读/离线复算，没有新的服务器运行查询。

独立验收PASS：1199载荷清单路径/大小无缺项，连两manifest共1201文件；298已读载荷上传/适用解码SHA通过，148618条矩阵/原始指标、19008次joint校验及固定gate复算匹配。未重读全部载荷、服务器权重/影像/预测/掩码本体。N2固定双向候选gate=False，S对空间控制−0.007028pp，方向/打乱增量均未过；按原门槛停止该3×3关系配方，不救窗口/预算/seed。

E1仅RGB缺失/H高DSM变化满足原N5问题门槛（A0/B1比U低0.651883/0.656097pp，两tile同号），L在RGB方向更容易；E0 N1-2 clean Full边界伤害率高于内部14.236/14.703pp，分母支持充足，但不能证明跨区传播是原因。E2 RGB漏报比硬回退约高1pp，误报完整RGB损失约6.4pp，DSM漏报效应小且跨tile异号；exact fallback不等于精度最优。

[完整报告](../POST_N2_E0_E1_E2_RESULTS_20261006.md)与[审计](../../../records/post_n2_offline_audit_20261006/README.md)。actual fixed22/selected32，与原代码/原件一致，继承文字已补正。关闭当前N2关系实现的新增贡献承诺，优先N5原四组匹配控制、N3随后；新族代码/训练未派发，N4不触发。研究路线角色、失败不追训、无T/Test6/追加seed保持。此前“待上传/等待/问题门槛”条目是带时间历史，不是当前状态。


## 2026-10-06扩展后续规划（不是实验结果）

[扩展规划](../../protocols/POST_N2_EXPANDED_PORTFOLIO_20261006.md)：N5=4、N3=5、N4=4，新增R1=4/R2=4条件储备，最多21训练配置；E3/E4/E5/E6为零新训练诊断。先N5，逐族判门槛；R1依赖E4，R2依赖N5/N3均成立。尚未实现/登记这些新族，不更新已完成数量、不改变旧失败去留。


## 2026-10-06 N5执行包已实现（运行结果待回报）

用户授权按扩展规划执行；第一批N5四组[冻结执行协议](../../protocols/POST_N5_EXECUTION_20261006.md)、code与CPU15项/语法11文件通过，[就绪记录](../../../records/post_n5_execution_design_20261006/validation.json)。尚无服务器登记/首步，不增加已完成数量。只GPU0/1、新8000步/组，固定N1-2state；先查原队列/锁，重复登记只返回既有N5。T在完整协议冻结后评价，不选模；后续条件族待证据与独立实现，不自动21组。


## 2026-10-06 N5登记已回报

最后服务器登记回报（用户终端，2026-10-06）：N5_QUEUE_REGISTERED，目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_n5_20261006T114819_71934，controller PID72265，TRAINING_JOBS=4，GPU0/1，NEW_STEPS=32000；nohup_20261006T114827023329.log。目录时间标记11:48:19、日志名11:48:27，不替代queue observed_at。未收到queue状态、controller/worker存活、mask进度或CUDA首步，不能声称正在训练。下一步只读查询这条N5，不重复登记或重启旧队列。

[登记原件转录](../../../records/research_post_n5_20261006T114819_71934/registration_observation.json)。登记不增加完成数量；前述待登记条目为历史准备态。


## 2026-10-06 N5处于CPU掩码准备

用户只读回报（2026-10-06）：queue LAST_OBSERVED=2026-10-06T11:48:28.739479+08:00，PREPARING_MASKS，controller PID72265 LIVE=True；N5四组PENDING、0/8000、worker PID−1。queue时间是进入CPU准备阶段时刻，不代表日志后续进度时刻。preparation.log已有13个唯一tile的N5_MASKS_COMPLETE，fit12全部12个及Val2 3_11已报告，预定5_10尚无完成行；未收到精确日志时间/准备完成标记/worker首步，未见本回报错误。准备结束自动派发GPU0 N5-0、GPU1 N5-1；只读继续观察，不重复启动。

[只读回报转录](../../../records/research_post_n5_20261006T114819_71934/preparing_masks_observation_20261006.json)。这些不是模型完成数，尚无N5精度。


## 2026-10-06 N5四组全部完成及原件验收

最后服务器回报：N5 queue观测2026-10-06T21:16:59.632381+08:00，N5_COMPLETE_AWAITING_REVIEW，四组COMPLETE/8000且selected全8000；用户status查询controller/worker LIVE=False（查询时刻未单列）。2026-10-06原件1bd58b6已收到，本次只做GitHub回读/离线复算，未新训练或GPU推理。

固定N5-3 gate=False、bilateral_candidate=False：T对随机N5-1仅+0.041878pp（要求≥0.5），clean/DSM全缺失对N5-0 −0.191071/−0.152271pp（底线−0.1）。RGB T在3_11负、5_10正。沿原冻结门槛关闭本次混合缺失配方的增量承诺，不换N5-2救gate、不扫比例/强度/预算/seed。普通适应仍是强控制，位置问题不整体关闭。

独立审计PASS：871载荷清单路径/大小匹配（连manifest872文件）；50载荷及manifest独立回读，124464次矩阵/原始指标与12304次joint校验，560个嵌入case重建匹配原源SHA，5040个预测索引绑定，固定gate/选模/监督与规则配额复算一致。未读取全部871载荷或服务器权重/影像/预测/mask本体；12项固定发布源码SHA匹配，44 mask元数据绑定匹配。

[结果](../POST_N5_RESULTS_20261006.md)、[审计](../../../records/post_n5_offline_audit_20261006/README.md)。N5-0/1/2/3 S_available=86.687264/86.365394/86.484846/86.392995，selected全8000。先E3与N5后边界复查，满足条件再N3；R2不激活，未登记新后继。前述N5待登记/掩码状态为带时间历史，不是当前状态。


## 2026-10-06 N5后交叉问题规划（未运行）
[24—48小时计划](../../protocols/POST_N5_CROSS_QUESTION_48H_PLAN_20261006.md)：E4-v2三因素8推理路径，区分输入清零/特征删除/输出回退；E3/N5边界复查保持。R1四组、N3五组、新S1四组共13候选，本窗口最多两族8—9组、诊断过门槛才启动。默认计算/诊断25—38h、加交接目标27—44h，实施时间另计。只是规划与源码/文献核对，无执行包/后继登记，不改既有N5/N2失败或原E2 gate。


## 2026-10-06 交叉问题诊断包就绪（未登记/运行）
[冻结执行协议](../../protocols/POST_N5_CROSS_DIAGNOSTICS_EXECUTION_20261006.md)：E3/N5后边界复用原预测，E4-v2三因素八路径、192推理单元、0训练，CPU17项与10文件语法通过。包含原路径一致/全缺失保护、真实控制器两lane与故障/超时、192模拟case独立汇总退出。CPU检查使用合成专家/数据，非服务器权重/DINO/GPU科学结果；服务器登记前同包检查。入口enqueue_post_n5_cross.py幂等防重复，完成后轻量上传并复算，再按既有授权落实至多两训练族，R1/N3/S1尚未实现可派发训练包。没有新服务器PID/目录/存活观测。


## 2026-10-06 23:55诊断登记回报（不是进度观测）
最新服务器登记回报（用户终端）：2026-10-06，新诊断目录research_post_n5_cross_20261006T235526_442218，控制器PID442590，NEW_TRAINING=0、E4_TILE_UNITS=192、GPU=0,1。目录时间标记23:55:26，nohup文件名时间23:55:38.454869；它们不是queue observed_at，尚未收到状态/存活/CPU阶段或GPU进度回报。原N5最后queue观测21:16:59已完成，未重启。
[登记摘录](../../../records/research_post_n5_cross_20261006T235526_442218/user_reported_registration_20261006.json)。下一步只读status及nohup/preparation日志；服务器CPU17项启动前成功返回为执行链推断，未单收检查日志。R1/N3/S1未派发，不重复登记或重启旧实验。


## 2026-10-07 00:00诊断两卡推理回报
最后服务器观测（用户终端）：QUERY_OBSERVED=2026-10-07T00:00:27.985817+08:00，queue LAST_OBSERVED=2026-10-07T00:00:27.169441+08:00，RUNNING_E4，控制器PID442590 LIVE=True；CPU=COMPLETE，新增optimizer更新0。GPU0 E4_N1-2 PID443709、GPU1 E4_N2-0 PID443712均RUNNING/LIVE=True，当前3_11、rgb_known_missing_A1B0C0；E4_N2-3在GPU0 PENDING。没有完成模型/科学gate回报。
CPU八条模型×tile准备日志已收，最后N5-3/5_10进度23:57:40；技术完成不等于问题gate过。未收E3/边界/screen计数或完整E4结果。继续已有队列，不重新登记、无新训练。[原始转录](../../../records/research_post_n5_cross_20261006T235526_442218/user_reported_running_20261007T000027.json)。


## 2026-10-07 07:38诊断完成回报（轻量原件待收）
最后服务器查询（用户终端）：QUERY_OBSERVED=2026-10-07T07:38:05.617099+08:00；queue最后更新2026-10-07T01:08:32.994625+08:00，CROSS_DIAGNOSTICS_COMPLETE_AWAITING_REVIEW。CPU完成，三个E4作业COMPLETE，查询时控制器及worker均LIVE=False，新增optimizer更新0。回报screen output=False、feature=True、boundary=True，NEXT_FAMILIES=['N3','S1']；原计数/绑定尚未上传验收。
RGB固定output增量N1-2/N2-0 −0.299884/+0.401156pp且两tile异号，不触发R1；C=0下feature增量+1.307603/+0.577591pp且两tile正，触发S1问题。DSM不支持双向收益。boundary screen=True，候选N3五组＋S1四组；原边界分母/192case未独立接收，先上传，不派发未实现训练。诊断约1h13m，各worker约35m。
[用户终端转录](../../../records/research_post_n5_cross_20261006T235526_442218/user_reported_complete_20261007T073805.json)。


## 2026-10-07：诊断原件验收与N3/S1执行包

诊断f60491f原件已收，独立复算PASS（352载荷路径/大小，238JSON+manifest，4128矩阵/1168joint，192case/576预测索引/106源码索引）。[完整结果](../POST_N5_CROSS_RESULTS_20261007.md)；原件/数组核验范围见审计README。R1跳过、N3/S1问题门槛通过，S1仅RGB C=0条件线索。N5/N2旧失败不改判。

用户授权接续九组；[冻结协议](../../protocols/POST_N3_S1_EXECUTION_20261007.md)，CPU17项/语法11执行Python文件通过，READY_NOT_REGISTERED，无新服务器运行回报。固定N1-2完整state/new8000×9/seed42/GPU0/1；23—34h粗范围首组校准。此前待上传/未实现条目为带时间历史，当前以START_HERE为准。



## 2026-10-07：九组服务器登记已回报

用户终端返回N3_S1_QUEUE_REGISTERED：目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_n3_s1_20261007T083203_694293，controller PID694658，TRAINING_JOBS=9、NEW_STEPS=72000、GPU=0,1；日志nohup_20261007T083216182460.log。目录08:32:03与日志08:32:16.182460是命名时间标记，不是queue observed_at。登记前同包CPU检查成功返回由执行链推断，尚未单收服务器检查日志。当前REGISTERED_PROGRESS_NOT_YET_QUERIED：未收到controller/worker存活、CPU准备状态、首步或完成回报，不能写为两卡训练已确认。此前READY_NOT_REGISTERED为发布时历史状态。

下一步只读新目录code/scripts/status_post_n3_s1.py与nohup/preparation日志；不再次enqueue、不重启旧N5/N2/cross。记录见records/research_post_n3_s1_20261007T083203_694293/registration_observation.json。估时23—34h仍为规划范围；只有实际启动/首个完整作业回报后校准，不能从登记PID推断精度结果或实时运行。


## 2026-10-07 08:41：N3双卡实际训练已确认

最后服务器只读查询（用户终端）：QUERY_OBSERVED=2026-10-07T08:41:47.885238+08:00，queue LAST_OBSERVED=2026-10-07T08:41:46.005396+08:00，RUNNING_N3_S1，controller PID694658 LIVE=True。GPU0 N3-0 PID694733 LIVE=True，training360/8000，progress08:41:42.634794、1.324986秒/步、训练剩2.811914h；GPU1 N3-1 PID694739 LIVE=True，training360/8000，progress08:41:43.547025、1.328100秒/步、训练剩2.818524h。两worker各加载12/12训练tile，峰值分配约36.79/36.80GB。N3-2/3/4与S1-0/1/2/3七项PENDING；0/9作业COMPLETE。日志确认两个START，无本次故障回报，没有精度或机制gate结果。

原目录research_post_n3_s1_20261007T083203_694293、执行0e22438a7131a0a1f28098e675c3367d40236398保持，不重新登记或重启。CPU准备已完成与登记前检查成功由RUNNING/派发执行链推断；没有单独preparation/check日志原件回读。记录见records/research_post_n3_s1_20261007T083203_694293/user_reported_running_20261007T084147.json。此前仅登记/进度未查询为带时间历史。

当前两组纯训练剩约2h49m，不含4000/8000验证及fixed/selected/U评价。假定后续步速相同，GPU0共五组（当前+四组）、GPU1共四组（当前+三组），训练本身最长lane剩约14.59h；这不是整队ETA，未测后续条件区域/S1及完整评价耗时。九组完整粗范围仍23—34h，从08:32登记参照约2026-10-08 07:30—18:30，非保证，首个完整作业后校准。不能把loss或360步可运行当方法有效。

下一步继续既有nohup队列，按需只读新目录status及日志；失败时保留worker与目录、明确诊断/接管，不自动重试/追加seed/别族。仅GPU0/1，zzx对应目录，无SSH/Test6/independent final/held4或重复资源审计。


## 2026-10-08：九组正常完成，原计数待上传验收

最后服务器查询（用户终端）：QUERY_OBSERVED=2026-10-08T22:11:10.555448+08:00；queue LAST_OBSERVED=2026-10-08T06:37:48.607436+08:00，N3_S1_COMPLETE_AWAITING_REVIEW，controller PID694658 LIVE=False。N3-0…4/S1-0…3九组全部COMPLETE、8000/8000，查询时全部worker LIVE=False。nohup完整派发/完成序列及独立汇总正常退出，无本次技术故障回报；不是控制器中断导致显卡空闲。

日志N3_S1_SCREEN False False False：N3固定候选、S1固定候选及bilateral_candidate均False（服务器汇总回报，尚未独立接收CM/joint/checkpoint/选模绑定）。不猜具体失败项或把loss当评价，不宣称两个研究问题整体不成立。原冻结门槛与主线保持，暂不扩大预算/区域超参/seed或换后验候选救门槛。完成态不自动派发后继族。

原执行0e22438a7131a0a1f28098e675c3367d40236398，原目录research_post_n3_s1_20261007T083203_694293保持。首波各约4h39m、其余完整worker约4h19m—4h23m；日志名2026-10-07 08:32:16.182460至queue完成2026-10-08 06:37:48.607436，粗墙钟约22h05m32s，命名起点不是独立精确启动观测。此前23—34h规划不再作为剩余ETA。

立即下一步：用户终端运行原目录code/scripts/upload_post_n3_s1_records.py --root ROOT --directory DIR，显式上传轻量原件；无需再次fetch/enqueue，不启动训练。接收原件后独立复算selected/fixed8000的S_available、QR/QD、U方向/tile、保护底线、单因素/网格控制、所有绑定与原始分母；区分增量不足、保护失败、方向不一致或简单控制已解释，再决定去留。科学原件与GPU权重/预测保留服务器，无Test6/independent final/held4、追加seed或重复资源审计。


## 2026-10-08：N3/S1九组原件已验收

[结果报告](../POST_N3_S1_RESULTS_20261008.md)、[独立审计](../../../records/post_n3_s1_offline_audit_20261008/README.md)。原件38d2055，九组全部selected8000，1508载荷路径/大小匹配，79JSON+manifest回读，227556矩阵/22140原joint边际池化、1044case/9396预测索引，12新科学源与执行0e22438逐字一致。未GPU复跑/本体重hash/全载荷回读。

N3-4 S对局部−0.000078pp/网格+0.001937pp，增量门槛失败；S1-3 RGB U对原策略+4.102047pp、DSM−0.023201pp，worst aux_shift8/3_11−0.391546pp违反−0.2保护。两gateFalse，S1双向False，具体配方去留保持。单向收益线索不自动升级主线，下一建议先复用预测诊断可靠性代价，未实现/登记。此前运行/待上传状态为带时间历史。

## 2026-10-08：Post-S1后续十组单卡规划（未执行）

[规划](../../protocols/POST_S1_SUPPORT_GPU0_PLAN_20261008.md)：基于已验收S1 RGB局部+4.102pp及退化保护失败，先D0复用/拼接与D1固定权重×策略诊断，再P十组（更新隔离×上下文支持×修正区域八组，另空间打乱/简单校准两组），E六压力条件；Q镜像DSM四组仅条件储备。P统一S1-0/new8000/seed42，固定8000主比较，P7候选事前指定。首轮约33—57h单卡预算，无科学总时限，不靠重跑/加seed填时长。

用户本次要求只能GPU0，覆盖所有后续GPU活动；旧GPU0/1文字是历史执行证据。本条是PLANNED_NOT_IMPLEMENTED_NOT_REGISTERED，无新队列/PID，不改变已完成数或旧gate。主线角色保持，具体去留/压力门槛/文献边界见规划。

## 2026-10-08：Post-S1 GPU0单卡执行包就绪（未登记）

用户授权按规划实施，[冻结协议](../../protocols/POST_S1_SUPPORT_EXECUTION_20261008.md)及model/worker/D0/D1/E/controller/status/summary/upload入口已实现，CPU22项和12Python语法通过，覆盖基座/冻结/原CE等价/空间打乱/native跨窗/单卡FIFO失败超时/原计数与完整汇总。合成CPU检查，非真实backbone/权重/GPU科学结果；服务器登记前同包再验。

READY_NOT_REGISTERED，无新服务器PID/目录/进度，不增加已完成数。只GPU0，十组新8000/seed42/固定S1-0、fixed8000主比较；D1 48新tile、E144新tile，Q仅条件储备不自动派发。入口幂等核原队列与锁，nohup，zzx新目录，故障停止后继无重试。旧N3/S1 gate和主线角色保持。[就绪记录](../../../records/post_s1_support_execution_design_20261008/validation.json)。

## 2026-10-08 23:49：Post-S1 GPU0队列服务器登记回报

最新服务器登记回报（用户终端，2026-10-08）：SUPPORT_QUEUE_REGISTERED，目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_s1_support_20261008T234921_1890161，controller PID1890742，GPU=0 ONLY，TRAINING_JOBS=10、NEW_STEPS=80000、Q_RESERVED_NOT_RUNNABLE=4；日志nohup_20261008T234938791083.log。目录23:49:21及日志23:49:38.791083为命名时间标记，不是queue observed_at。当前REGISTERED_PROGRESS_NOT_YET_QUERIED，尚无controller/worker存活、D0/D1进度、CUDA首步或完成回报，不能写为训练已确认。

原队列登记前检查回报：最后观测2026-10-08T06:37:48.607436+08:00，COMPLETE RELEASED。登记前CPU检查成功返回由执行入口链推断，服务器cpu_checks.log尚未单独接收；本地22项/12Python语法检查保持其合成CPU范围。

执行2c5e7d6f383cfe454415d4e106179930264f1141保持；D0→D1→P十组→E已登记，Q四组仅不可运行储备。只GPU0、nohup、zzx对应目录，无新增科学完成数。下一步只读既有队列，不重复enqueue，不从PID或显卡占用推断方法有效。[登记摘录](../../../records/research_post_s1_support_20261008T234921_1890161/registration_observation.json)。

## 2026-10-08 23:53：Post-S1 D0 CPU准备进度已确认

最后服务器只读查询（用户终端）：QUERY_OBSERVED=2026-10-08T23:53:14.323317+08:00，queue LAST_OBSERVED=2026-10-08T23:49:50.130388+08:00，PREPARING_D0_MASKS，controller PID1890742 LIVE=True；CPU=RUNNING。CPU_PROGRESS在23:51:48.651736报告D0 / 3_11 / rgb_U。D1、P6/P7/P8/P9/P4/P5/P2/P3/P0/P1、E十二项全部PENDING、PID−1、LIVE=False，无CUDA首步或科学结果。Q=RESERVED_NOT_AUTOMATIC。当前显卡空闲符合CPU准备阶段，未见本次错误回报；不能据此宣布D0完成或训练已开始。

既有登记保持：执行2c5e7d6f383cfe454415d4e106179930264f1141，目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_s1_support_20261008T234921_1890161，nohup_20261008T234938791083.log，GPU0 ONLY，10训练/80000新步；Q四组不可运行储备。登记前CPU检查成功返回由入口执行链推断，服务器检查日志未单收。

此前登记/进度待查询条目为带时间历史。0/10新训练完成、0个GPU作业启动回报；不更新科学gate或独立验收范围。继续已有nohup队列，按需同一status只读检查，不重新enqueue、不自动追加Q/GPU1/seed。[用户只读回报](../../../records/research_post_s1_support_20261008T234921_1890161/user_reported_d0_progress_20261008T235314.json)。

## 2026-10-09 21:25：Post-S1 GPU0运行P3，七训练作业完整结束

最后服务器只读查询（用户终端）：QUERY_OBSERVED=2026-10-09T21:25:10.899578+08:00；queue LAST_OBSERVED=21:25:10.879724，RUNNING_P3，controller PID1890742 LIVE=True，仅GPU0。CPU=COMPLETE、D1 COMPLETE（0更新，约43分01秒）；P6/P7/P8/P9/P4/P5/P2七组COMPLETE/8000，worker LIVE=False。P3 PID2437737 LIVE=True、8000/8000，checkpoint_selection阶段，正在3_11/dsm_missing的验证/评价；该标签继承旧进度命名，本轮主比较仍固定8000。P0/P1和E PENDING；Q=RESERVED_NOT_AUTOMATIC。没有本次故障回报，尚无科学分数/屏幕门槛/轻量原件验收，不能用loss或完成状态判有效。

截至21:25的条件估时：还需约10—14h，参照约2026-10-10 07:25—11:25（Asia/Shanghai），非保证。六冻结完整worker实测约1h56m—2h31m，P2共享更新完整worker3h57m53s；P3已训练完但完整评价剩余未测，另两共享组预计各约4h，E仍按1.5—4h规划及汇总开销估算。不是只用remaining_train_hours=0推断整队已完，也不含Q四组。

执行2c5e7d6f383cfe454415d4e106179930264f1141、目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_s1_support_20261008T234921_1890161、controller1890742、nohup_20261008T234938791083.log保持，不重复enqueue或重启旧队列。十P各new8000/seed42/固定S1-0 state、fixed8000主比较，P7为事前指定候选；本次只是带时间进度，不更改科学协议或去留。

CPU/D1完成且七worker已完整返回，其余P3评价→P0/P1→E继续自动串行。科学原计数/门槛未收到，不从loss宣称P7有效或增论文验证数。[用户终端进度](../../../records/research_post_s1_support_20261008T234921_1890161/user_reported_progress_20261009T212510.json)。此前CPU准备/待首步条目为历史观测。

## 2026-10-09 21:31：用户授权先上传完整作业快照并分析

CPU/D1与七P完整，P3在fixed8000评价3_11/aux_down4，controller LIVE，P0/P1/E待运行。[独立上传入口](../../protocols/POST_S1_COMPLETED_SNAPSHOT_ANALYSIS_20261009.md)只冻结COMPLETE名单与D0/R0/基线轻量原件，6项stdlib检查通过，不改科学快照/不暂停训练。当前未收到上传commit/精度数据，待用户终端执行后离线复算；未齐E/共享八格不得判最终gate或双向贡献。记录见records/research_post_s1_support_20261008T234921_1890161/user_reported_progress_20261009T213111.json。


## 2026-10-09：七P完整快照已接收并独立分析

原件77d3970f，快照21:43:00、queue最后观测21:42:23，D1/P6/P7/P8/P9/P4/P5/P2完整，P3 RUNNING、P0/P1/E PENDING。[阶段结果](../POST_S1_PARTIAL_RESULTS_20261009.md)，[独立审计](../../../records/post_s1_partial_offline_audit_20261009/README.md)。1474路径/大小、145次JSON读取（3重读）、203292矩阵/22176joint、1032case/8328预测索引、12科学源执行回读通过；非全载荷/数组本体重hash或GPU复跑。

P7 RGB_U 83.575357%，对基线+2.562756、P6+1.759726、P8+1.952962、P9+2.207993pp，两tile正；普通/全缺失/DSM_U保护0变化。R0 85.001650%，P7−R0 −1.426292pp（两tile负）违反固定−0.2pp必要条件。P7具体gate失败；E未收，完整压力未验。D1固定DSM信号−0.050601pp且tile异号，Q必要条件失败、仍不运行。保留单向上下文线索，主线/旧gate不变；剩余三P/E继续原GPU0 FIFO，不能后验换候选/追加seed。此前“尚无科学原件”条目是历史状态。

最新注册依据：[终端回报](../../../records/post_s1_transfer_registration_20261010/observation.json)；执行目录research_post_s1_transfer_20261010T073327_2852696，PID2852987，未收到后续存活或T0训练回报。
