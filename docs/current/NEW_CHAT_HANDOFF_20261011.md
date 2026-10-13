# 新对话入口：Phase1.5 CPU分析中（更新2026-10-13）

## 最新观测：100批GPU完成，CPU分析进行中（2026-10-13 10:17）

用户只读查询 **QUERY_OBSERVED=2026-10-13T10:17:19.241427+08:00**；queue **LAST_OBSERVED=2026-10-13T10:17:18.524905+08:00**，**CPU_ORACLE_AND_CONDITIONAL_COUNTS / CONTROLLER_LIVE=True**，**COMPLETE=100**。nohup包含GPU0/1交错派发和完成，末尾 `PHASE15_JOB_COMPLETE B_16_5_10 GPU 1`、`PHASE15_JOB_COMPLETE D_16_5_10 GPU 0`；没有此次错误回报。两卡GPU批次全部返回完成，显卡空闲符合CPU阶段，并非单卡未启动或据此认定失败。以上为最后观测，不是实时状态。

按已发布控制器执行链，到达此阶段意味着两卡真实smoke自动验收、100批accept_job绑定检查、E子进程成功返回；这些是执行链推断，尚未独立接收PASS/CM/预测绑定/E原件，不等于科学验收或方法有效性。整轮尚未达到PHASE15_COMPLETE_AWAITING_REVIEW；当前CPU D对2tile×20旧mask ID×4family共160case做五专家互补/oracle及可观测条件计数，之后汇总A/B/C/D/E。D进度见 `analysis/D/progress.json`，日志 `logs/analysis_D.log`；completed_cases是CPU D的160case进度，不是新GPU批数。

修复commit `45138f0f92c668bc86ce9532a4382b38d2b12b6d`、目录 `research_phase15_recoverability_20261012T233532_842792`、登记PID843079、日志 `nohup_20261012T233542741074.log` 保持。0训练/100固定批/1540唯一逻辑case、无新增seed/Test6/held4/final；旧失败目录保留，不再登记/重启。当前GPU部分已完成，之前24–48h资源预留不能继续当剩余ETA；CPU D完成量/步速未回传，暂不报剩余小时。

下一步继续现有CPU分析→五项汇总，仅读取status及D进度。达到PHASE15_COMPLETE_AWAITING_REVIEW且owned进程/锁退出后，用原目录upload_phase15.py前台上传轻量原件，再独立核验、分析并据科学去留条件制定配对训练。不会自动派发新训练；若CPU/HOLD失败保留原件，不自动重试。

[本次用户进度原件](../../records/research_phase15_recoverability_20261012T233532_842792/user_reported_cpu_analysis_20261013T101719.json)。

---

## 历史修复记录：已定位路径错误，发布时待接管

用户补充的GPU0子日志定位到 `phase15_inference.py` 输入绑定记录路径：`self.base/'input_binding_last_'+str(self.gpu)+'.json'`，因运算优先级先生成Path再加字符串，触发 `TypeError: unsupported operand type(s) for +: 'PosixPath' and 'str'`。已改为 `self.base/('input_binding_last_'+str(self.gpu)+'.json')`。xFormers提示不是该退出根因；没有smoke通过或方法有效性证据。失败发生在写出case记录之后、返回之前，原partial产物不能当smoke验收通过。

本地22项CPU检查与13文件AST通过，新增实际绑定写入语句的GPU0/1回归、显式接管拒绝条件检查；不等于服务器真实CUDA验证。发布时修复状态 **REPAIR_READY_NOT_REGISTERED**；原目录最后观测仍为SMOKE_FAILED_HOLD、100 PENDING、controller非存活（查询2026-10-12T23:28:06.269038+08:00，queue23:27:34.651175）。新PID/目录未回传。

用户终端使用修复发布commit的enqueue入口及显式 `--replace-path-bug-directory OLD_DIR`。仅允许本次原commit/原目录/已确认错误、全100 PENDING、无GPU1 smoke、无存活controller/stage/E/job且锁释放的替代；只允许一个既有原目录。第二次调用发现替代目录就停止登记。保留旧源码/日志/产物，新技术执行目录记录旧plan/code/status/failure/log SHA，不复用失败case缓存；重做准备/CPU22项/真实smoke，smoke全PASS后继续相同100批/1540唯一逻辑case。不是新科学矩阵、追加seed或自动重试；以后任何新失败仍HOLD不自动接管。原旧队列不重启，不访问Test6/held4/final。

---

## 最后服务器观测（历史回报）：GPU0 smoke失败，停止全量（2026-10-12 23:28）

用户终端只读查询 QUERY_OBSERVED=2026-10-12T23:28:06.269038+08:00；queue LAST_OBSERVED=2026-10-12T23:27:34.651175+08:00，**SMOKE_FAILED_HOLD**，CONTROLLER_LIVE=False，100批全部PENDING。主日志为 `smoke_phase15.py exit=1`，发生在GPU0 smoke子进程；GPU1 smoke及全量未派发。准备脚本成功返回由控制器到达此阶段的执行链推断，不等于独立验收准备原件。主日志未包含子进程根因，不能认定为OOM、权重或矩阵一致性问题；无新科学结论。

执行commit与原目录保持。下一步仅读取原目录 `logs/smoke_gpu0.log`、`technical_failure.json`、`smoke/gpu0/progress.json`（若存在），必要时上传HOLD轻量原件。不得重复enqueue、删除缓存、绕过smoke或自动重试；根因明确后再落实有版本记录的技术修复。旧科学gate及固定诊断范围不变。此前登记/待查询状态为历史。

[用户失败回报](../../records/research_phase15_recoverability_20261012T232212_836118/user_reported_smoke_failure_20261012T232806.json)。

---


2026-10-12用户终端已返回 **PHASE15_REGISTERED**，登记时证据状态为 **REGISTERED_PROGRESS_NOT_YET_QUERIED**。执行commit `7b12fec6d7fb451e09316ba59f7d62ca8e0c316b`；目录 `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase15_recoverability_20261012T232212_836118`，登记controller PID836482，日志 `nohup_20261012T232227296552.log`。目录23:22:12与日志23:22:27.296552仅为命名时间标记，不是queue observed_at；尚无只读进度查询、controller/worker存活确认或真实smoke结果。

GPU0/1、100工作批次、1540唯一逻辑case（两S1 clean缓存复用，按最多1538新tile推理计），0训练/0优化器更新。24–48h为预留范围，非当前剩余ETA；无24h总截止。登记前同包CPU检查成功返回由入口执行链推断，服务器cpu_checks.log尚未单独接收；本地20项合成CPU检查及13新Python语法通过不等于真实CUDA/权重验收。

启动入口enqueue_phase15.py幂等检查旧完成队列/锁，继承immutable源码→CPU检查→准备→GPU0真实smoke(ID1/tile3_11)→GPU1同case一致性→自动技术验收全PASS→双卡全量→五项汇总。任一技术失败HOLD且停止拥有的children，不自动retry或加训练。用户终端执行、无SSH，全部记录/缓存/临时产物在/home/jovyan/zzx新目录。

旧两轮最后上传观测：Post-T 2026-10-12T11:03:22.917566+08:00，8/8 COMPLETE、PAIRED_SCREEN=False；Structured 2026-10-12T16:32:44.762198+08:00，42/42 COMPLETE、NO_SUPPORT_THIS_PROTOCOL。不是当前服务器实时查询。R16−H16+0.348562pp局部门槛通过，总失败来自5/6 E−R0底线；独立预算未支持盲目续训，但R16自身后8k仍+0.618217pp。S1主PE+0.122522pp/CI跨0，RGB-only+3.119077pp；旧gate不改。

先读[研究决定](RESEARCH_DECISION.md)→[HANDOFF](HANDOFF.md)→[状态](PROJECT_STATUS.md)→[下一步](NEXT_EXPERIMENT.md)，再读执行协议和实际原件。用户本次授权已明确，不重问；没有服务器直连；用户已执行固定commit bootstrap，后续只读原目录。

新对话复用已经通过且绑定不变的CPU检查，不因换电脑重做旧科学审计。服务器启动前同包CPU是当前执行环境绑定检查；真实smoke通过后自动全量，任何负/高oracle都不能自动加新训练。

[执行协议](../protocols/PHASE_1_5_EXECUTION_20261012.md)、[完整设计](../protocols/PHASE_1_5_RECOVERABILITY_20261012.md)、[双卡规划](../protocols/PHASE_1_5_TWO_GPU_PLAN_20261012.md)、[CPU验证记录](../../records/phase15_execution_design_20261012/validation.json)。

登记原始回报：[轻量摘录](../../records/research_phase15_recoverability_20261012T232212_836118/registration_observation.json)。下一步只读 `PY -B DIR/code/scripts/status_phase15.py --directory DIR` 与原nohup日志；进度未收前不认定双卡已开始。
