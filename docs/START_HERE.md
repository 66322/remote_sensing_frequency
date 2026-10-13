# 共享入口：Phase1.5 GPU完成，CPU分析中（2026-10-13）

## 最新登记：CPU双进程加速已接管，进度待查询（2026-10-13）

用户终端返回 `CPU_ACCELERATION_CONTROLLED_STOP_D 1099918 PRESERVE_COMPLETED_CASES`，随后 **CPU_ACCELERATION_REGISTERED**，子目录 `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase15_recoverability_20261012T233532_842792/cpu_acceleration_20261013T110244_1189050`，登记PID1189233、WORKERS=2，日志 `controller.log`。执行commit `4842b5eb38c62b19db97094d88526260f5fe3359`。当前证据状态 **CPU_ACCELERATION_REGISTERED_PROGRESS_NOT_YET_QUERIED**；目录11:02:44为命名时间标记，不是queue observed_at。尚无新控制器存活查询、真实pixel/matched等价回执或并行新case计数，不从PID宣称真实检查PASS。

成功登记执行链推断：同包CPU检查、资源门禁、原D身份核对、受控停止、等待原controller/child退出及锁释放已返回；接管前后状态/完成case保留清单尚未独立接收。原GPU100批结果与原plan/code保持；原分析停止时的HOLD为明确受控接管历史，不能当新科学配方失败。新controller先扫描/绑定已完成case并对照两个真实结果，PASS后两CPU进程分派剩余case、最终调用原五项汇总。原D最后回传57/160（10:44:37）不是接管时保留数，应以后续progress为准。

立即下一步只读原 `status_phase15.py --directory DIR`、新 `cpu_acceleration_20261013T110244_1189050/controller.log`，及 `analysis/D/progress.json`。如存在 `cpu_acceleration_20261013T110244_1189050/real_equivalence.json` 可读取。不要再次accelerate/enqueue/手工启动GPU；原nohup已停止，后续诊断看新日志。旧约16:00 D ETA仅是接管前旧步速估计，不能沿用新任务剩余ETA；实际新completed_cases/elapsed后再校准。

固定0训练/100GPU批/160D case，0新增case/seed/Test6/held4/final，无GPU重跑。所有新增执行证据在原zzx目录子树，完成或HOLD且owned进程/锁退出后用原upload_phase15.py上传轻量原件，再做科学核验与配对训练选路。详见[CPU接管协议](protocols/PHASE_1_5_CPU_ACCELERATION_20261013.md)。

[用户接管登记原件](../records/research_phase15_recoverability_20261012T233532_842792/cpu_acceleration_20261013T110244_1189050/registration_observation.json)。

---


## 接管前最后CPU进度与耗时解释（2026-10-13 10:44）

用户读取D progress：10:17:47.026717为48case，10:35:41.565092为54case，**最后progress观测2026-10-13T10:44:37.604759+08:00为57/160case**（tile3_11/realization15/pixel），analysis_D日志tail空。该回报没有新queue查询或controller存活检查；最后queue观测仍10:17:18.524905、CPU_ORACLE_AND_CONDITIONAL_COUNTS/controller LIVE=True、GPU100 COMPLETE。CPU计数持续增长，不能按显卡空闲认定停止；此为最后观测而非实时。

检查修复执行commit45138f0f的analyze_phase15.py/phase15_numeric.py/control_phase15.py：D为单CPU子进程，OMP/OPENBLAS/MKL线程数1；每case校验/解压预测与熵，计算5专家及raw/smoothed组合、pixel/128/256 oracle，多区域int64 CM/新错恢复计数、距离变换、连通域、GT/可观测分箱。evidence与condition_counts存在重复全图扫描，当前实现可优化，但尚无函数级计时，不能指定实际唯一瓶颈或宣称CPU单核满载。线程设为1限制数值库并行，不意味着所有NumPy操作改线程就能提速。

48→57历时1610.578秒，9case平均178.953秒（约2分59秒）；按同速剩103case约5h07m，D预计2026-10-13 15:52左右，用户沟通取16:00左右。仅条件线性估计，mask族/第二tile/IO速度变化均可改变；不包含随后五项汇总，不是全队完成保证。原24–48h为资源预留，不用于当前剩余ETA。

保留现有执行快照与已完成57case，不中断/热改/自动重跑；未来技术优化可考虑缓存重复数组、复用valid/disagreement与联合计数、减少全图扫描，需严格整数结果等价检查，尚未实施。固定0训练/100GPU批/160D case，旧失败证据保留。继续只读D progress/status，全部分析汇总完成并owned进程/锁退出后上传轻量原件，独立科学验收后再制定配对训练；不自动新训练/seed/Test6/held4/final。

[三次CPU进度与条件估时](../records/research_phase15_recoverability_20261012T233532_842792/user_reported_cpu_progress_20261013T104437.json)。

---

## 历史修复记录：已定位路径错误，发布时待接管

用户补充的GPU0子日志定位到 `phase15_inference.py` 输入绑定记录路径：`self.base/'input_binding_last_'+str(self.gpu)+'.json'`，因运算优先级先生成Path再加字符串，触发 `TypeError: unsupported operand type(s) for +: 'PosixPath' and 'str'`。已改为 `self.base/('input_binding_last_'+str(self.gpu)+'.json')`。xFormers提示不是该退出根因；没有smoke通过或方法有效性证据。失败发生在写出case记录之后、返回之前，原partial产物不能当smoke验收通过。

本地22项CPU检查与13文件AST通过，新增实际绑定写入语句的GPU0/1回归、显式接管拒绝条件检查；不等于服务器真实CUDA验证。发布时修复状态 **REPAIR_READY_NOT_REGISTERED**；原目录最后观测仍为SMOKE_FAILED_HOLD、100 PENDING、controller非存活（查询2026-10-12T23:28:06.269038+08:00，queue23:27:34.651175）。新PID/目录未回传。

用户终端使用修复发布commit的enqueue入口及显式 `--replace-path-bug-directory OLD_DIR`。仅允许本次原commit/原目录/已确认错误、全100 PENDING、无GPU1 smoke、无存活controller/stage/E/job且锁释放的替代；只允许一个既有原目录。第二次调用发现替代目录就停止登记。保留旧源码/日志/产物，新技术执行目录记录旧plan/code/status/failure/log SHA，不复用失败case缓存；重做准备/CPU22项/真实smoke，smoke全PASS后继续相同100批/1540唯一逻辑case。不是新科学矩阵、追加seed或自动重试；以后任何新失败仍HOLD不自动接管。原旧队列不重启，不访问Test6/held4/final。

---

## 最后服务器观测（历史回报）：GPU0 smoke失败，停止全量（2026-10-12 23:28）

用户终端只读查询 QUERY_OBSERVED=2026-10-12T23:28:06.269038+08:00；queue LAST_OBSERVED=2026-10-12T23:27:34.651175+08:00，**SMOKE_FAILED_HOLD**，CONTROLLER_LIVE=False，100批全部PENDING。主日志为 `smoke_phase15.py exit=1`，发生在GPU0 smoke子进程；GPU1 smoke及全量未派发。准备脚本成功返回由控制器到达此阶段的执行链推断，不等于独立验收准备原件。主日志未包含子进程根因，不能认定为OOM、权重或矩阵一致性问题；无新科学结论。

执行commit与原目录保持。下一步仅读取原目录 `logs/smoke_gpu0.log`、`technical_failure.json`、`smoke/gpu0/progress.json`（若存在），必要时上传HOLD轻量原件。不得重复enqueue、删除缓存、绕过smoke或自动重试；根因明确后再落实有版本记录的技术修复。旧科学gate及固定诊断范围不变。此前登记/待查询状态为历史。

[用户失败回报](../records/research_phase15_recoverability_20261012T232212_836118/user_reported_smoke_failure_20261012T232806.json)。

---


权威分支66322/remote_sensing_frequency / rebuild-v1-protocol-20260915。

2026-10-12用户终端已返回 **PHASE15_REGISTERED**，登记时证据状态为 **REGISTERED_PROGRESS_NOT_YET_QUERIED**。执行commit `7b12fec6d7fb451e09316ba59f7d62ca8e0c316b`；目录 `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase15_recoverability_20261012T232212_836118`，登记controller PID836482，日志 `nohup_20261012T232227296552.log`。目录23:22:12与日志23:22:27.296552仅为命名时间标记，不是queue observed_at；尚无只读进度查询、controller/worker存活确认或真实smoke结果。

GPU0/1、100工作批次、1540唯一逻辑case（两S1 clean缓存复用，按最多1538新tile推理计），0训练/0优化器更新。24–48h为预留范围，非当前剩余ETA；无24h总截止。登记前同包CPU检查成功返回由入口执行链推断，服务器cpu_checks.log尚未单独接收；本地20项合成CPU检查及13新Python语法通过不等于真实CUDA/权重验收。

启动入口enqueue_phase15.py幂等检查旧完成队列/锁，继承immutable源码→CPU检查→准备→GPU0真实smoke(ID1/tile3_11)→GPU1同case一致性→自动技术验收全PASS→双卡全量→五项汇总。任一技术失败HOLD且停止拥有的children，不自动retry或加训练。用户终端执行、无SSH，全部记录/缓存/临时产物在/home/jovyan/zzx新目录。

旧两轮最后上传观测：Post-T 2026-10-12T11:03:22.917566+08:00，8/8 COMPLETE、PAIRED_SCREEN=False；Structured 2026-10-12T16:32:44.762198+08:00，42/42 COMPLETE、NO_SUPPORT_THIS_PROTOCOL。不是当前服务器实时查询。R16−H16+0.348562pp局部门槛通过，总失败来自5/6 E−R0底线；独立预算未支持盲目续训，但R16自身后8k仍+0.618217pp。S1主PE+0.122522pp/CI跨0，RGB-only+3.119077pp；旧gate不改。

主线RGB–DSM双向条件互补与退化/缺失，恢复旁支。五项诊断齐全再选方法，routing/context都是条件候选，不自动训练、不扩mask/seed、不加载Test6/held4/final。

先读[新交接](current/NEW_CHAT_HANDOFF_20261011.md)→[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一实验](current/NEXT_EXPERIMENT.md)→[执行协议](protocols/PHASE_1_5_EXECUTION_20261012.md)→[设计](protocols/PHASE_1_5_RECOVERABILITY_20261012.md)与原件。立即下一步是只读查询已登记Phase1.5原目录；不得重复bootstrap/enqueue。

登记原始回报：[轻量摘录](../records/research_phase15_recoverability_20261012T232212_836118/registration_observation.json)。下一步只读 `PY -B DIR/code/scripts/status_phase15.py --directory DIR` 与原nohup日志；进度未收前不认定双卡已开始。
