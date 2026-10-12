# 新对话入口：Phase1.5已登记（更新2026-10-12）

## 最新观测：GPU0 smoke失败，停止全量（2026-10-12 23:28）

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
