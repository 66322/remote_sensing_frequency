# 共享入口：Phase1.5已登记，进度待查询（2026-10-12）

权威分支66322/remote_sensing_frequency / rebuild-v1-protocol-20260915。

2026-10-12用户终端已返回 **PHASE15_REGISTERED**，当前证据状态为 **REGISTERED_PROGRESS_NOT_YET_QUERIED**。执行commit `7b12fec6d7fb451e09316ba59f7d62ca8e0c316b`；目录 `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase15_recoverability_20261012T232212_836118`，登记controller PID836482，日志 `nohup_20261012T232227296552.log`。目录23:22:12与日志23:22:27.296552仅为命名时间标记，不是queue observed_at；尚无只读进度查询、controller/worker存活确认或真实smoke结果。

GPU0/1、100工作批次、1540唯一逻辑case（两S1 clean缓存复用，按最多1538新tile推理计），0训练/0优化器更新。24–48h为预留范围，非当前剩余ETA；无24h总截止。登记前同包CPU检查成功返回由入口执行链推断，服务器cpu_checks.log尚未单独接收；本地20项合成CPU检查及13新Python语法通过不等于真实CUDA/权重验收。

启动入口enqueue_phase15.py幂等检查旧完成队列/锁，继承immutable源码→CPU检查→准备→GPU0真实smoke(ID1/tile3_11)→GPU1同case一致性→自动技术验收全PASS→双卡全量→五项汇总。任一技术失败HOLD且停止拥有的children，不自动retry或加训练。用户终端执行、无SSH，全部记录/缓存/临时产物在/home/jovyan/zzx新目录。

旧两轮最后上传观测：Post-T 2026-10-12T11:03:22.917566+08:00，8/8 COMPLETE、PAIRED_SCREEN=False；Structured 2026-10-12T16:32:44.762198+08:00，42/42 COMPLETE、NO_SUPPORT_THIS_PROTOCOL。不是当前服务器实时查询。R16−H16+0.348562pp局部门槛通过，总失败来自5/6 E−R0底线；独立预算未支持盲目续训，但R16自身后8k仍+0.618217pp。S1主PE+0.122522pp/CI跨0，RGB-only+3.119077pp；旧gate不改。

主线RGB–DSM双向条件互补与退化/缺失，恢复旁支。五项诊断齐全再选方法，routing/context都是条件候选，不自动训练、不扩mask/seed、不加载Test6/held4/final。

先读[新交接](current/NEW_CHAT_HANDOFF_20261011.md)→[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一实验](current/NEXT_EXPERIMENT.md)→[执行协议](protocols/PHASE_1_5_EXECUTION_20261012.md)→[设计](protocols/PHASE_1_5_RECOVERABILITY_20261012.md)与原件。立即下一步是只读查询已登记Phase1.5原目录；不得重复bootstrap/enqueue。

登记原始回报：[轻量摘录](../records/research_phase15_recoverability_20261012T232212_836118/registration_observation.json)。下一步只读 `PY -B DIR/code/scripts/status_phase15.py --directory DIR` 与原nohup日志；进度未收前不认定双卡已开始。
